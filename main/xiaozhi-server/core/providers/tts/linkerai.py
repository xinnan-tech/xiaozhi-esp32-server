import queue
import asyncio
import traceback
import aiohttp
import requests
import time
from config.logger import setup_logging
from core.utils.tts import MarkdownCleaner
from core.providers.tts.base import TTSProviderBase
from core.utils import opus_encoder_utils, textUtils
from core.providers.tts.dto.dto import SentenceType, ContentType, InterfaceType

TAG = __name__
logger = setup_logging()


class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.interface_type = InterfaceType.SINGLE_STREAM
        self.access_token = config.get("access_token")
        self.voice = config.get("voice")
        self.api_url = config.get("api_url")
        self.audio_format = "pcm"
        self.before_stop_play_files = []
        self.segment_count = 0  # 添加片段计数器

        # 创建Opus编码器
        self.opus_encoder = opus_encoder_utils.OpusEncoderUtils(
            sample_rate=16000, channels=1, frame_size_ms=60
        )

        # 添加文本缓冲区
        self.text_buffer = ""

        # PCM缓冲区
        self.pcm_buffer = bytearray()

    ###################################################################################
    # linkerai单流式TTS重写父类的方法--开始
    ###################################################################################

    def tts_text_priority_thread(self):
        """流式文本处理线程"""
        while not self.conn.stop_event.is_set():
            try:
                message = self.tts_text_queue.get(timeout=1)
                if message.sentence_type == SentenceType.FIRST:
                    # 初始化参数
                    self.tts_stop_request = False
                    self.processed_chars = 0
                    self.tts_text_buff = []
                    self.segment_count = 0
                    self.tts_audio_first_sentence = True
                    self.before_stop_play_files.clear()
                elif ContentType.TEXT == message.content_type:
                    self.tts_text_buff.append(message.content_detail)
                    segment_text = self._get_segment_text()
                    if segment_text:
                        self.to_tts_single_stream(segment_text)

                elif ContentType.FILE == message.content_type:
                    logger.bind(tag=TAG).info(
                        f"添加音频文件到待播放列表: {message.content_file}"
                    )
                    self.before_stop_play_files.append(
                        (message.content_file, message.content_detail)
                    )

                if message.sentence_type == SentenceType.LAST:
                    # 处理剩余的文本
                    self._process_remaining_text(True)

            except queue.Empty:
                continue
            except Exception as e:
                logger.bind(tag=TAG).error(
                    f"处理TTS文本失败: {str(e)}, 类型: {type(e).__name__}, 堆栈: {traceback.format_exc()}"
                )

    def _process_remaining_text(self, is_last=False):
        """处理剩余的文本并生成语音

        Returns:
            bool: 是否成功处理了文本
        """
        full_text = "".join(self.tts_text_buff)
        remaining_text = full_text[self.processed_chars :]
        if remaining_text:
            segment_text = textUtils.get_string_no_punctuation_or_emoji(remaining_text)
            if segment_text:
                self.to_tts_single_stream(segment_text, is_last)
                self.processed_chars += len(full_text)
            else:
                self._process_before_stop_play_files()
        else:
            self._process_before_stop_play_files()

    def to_tts_single_stream(self, text, is_last=False):
        try:
            max_repeat_time = 5
            text = MarkdownCleaner.clean_markdown(text)
            try:
                asyncio.run(self.text_to_speak(text, is_last))
            except Exception as e:
                logger.bind(tag=TAG).warning(
                    f"语音生成失败{5 - max_repeat_time + 1}次: {text}，错误: {e}"
                )
                max_repeat_time -= 1

            if max_repeat_time > 0:
                logger.bind(tag=TAG).info(
                    f"语音生成成功: {text}，重试{5 - max_repeat_time}次"
                )
            else:
                logger.bind(tag=TAG).error(
                    f"语音生成失败: {text}，请检查网络或服务是否正常"
                )
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to generate TTS file: {e}")
        finally:
            return None

    ###################################################################################
    # linkerai单流式TTS重写父类的方法--结束
    ###################################################################################

    async def text_to_speak(self, text, is_last):
        """流式处理TTS音频，每句只推送一次音频列表"""
        await self._tts_request(text, is_last)

    async def close(self):
        """资源清理"""
        await super().close()
        if hasattr(self, "opus_encoder"):
            self.opus_encoder.close()

    async def _tts_request(self, text: str, is_last: bool) -> None:
        params = {
            "tts_text": text,
            "spk_id": self.voice,
            "frame_durition": 60,
            "stream": "true",
            "target_sr": 16000,
            "audio_format": "pcm",
            "instruct_text": "请生成一段自然流畅的语音",
        }
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        # 一帧 PCM 所需字节数：60 ms &times; 16 kHz &times; 1 ch &times; 2 B = 1 920
        frame_bytes = int(
            self.opus_encoder.sample_rate
            * self.opus_encoder.channels  # 1
            * self.opus_encoder.frame_size_ms
            / 1000
            * 2
        )  # 16-bit = 2 bytes

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.api_url, params=params, headers=headers, timeout=10
                ) as resp:

                    if resp.status != 200:
                        logger.error(f"TTS请求失败: {resp.status}, {await resp.text()}")
                        self.tts_audio_queue.put((SentenceType.LAST, [], None))
                        return

                    self.pcm_buffer.clear()
                    opus_datas_cache = []

                    self.tts_audio_queue.put((SentenceType.FIRST, [], text))

                    # 兼容 iter_chunked / iter_chunks / iter_any
                    async for chunk in resp.content.iter_any():
                        data = chunk[0] if isinstance(chunk, (list, tuple)) else chunk
                        if not data:
                            continue

                        # 拼到 buffer
                        self.pcm_buffer.extend(data)

                        # 够一帧就编码
                        while len(self.pcm_buffer) >= frame_bytes:
                            frame = bytes(self.pcm_buffer[:frame_bytes])
                            del self.pcm_buffer[:frame_bytes]

                            opus = self.opus_encoder.encode_pcm_to_opus(
                                frame, end_of_stream=False
                            )
                            if opus:
                                if self.segment_count < 10:  # 前10个片段直接发送
                                    self.tts_audio_queue.put(
                                        (SentenceType.MIDDLE, opus, None)
                                    )
                                    self.segment_count += 1
                                else:
                                    opus_datas_cache.extend(opus)

                    # flush 剩余不足一帧的数据
                    if self.pcm_buffer:
                        opus = self.opus_encoder.encode_pcm_to_opus(
                            bytes(self.pcm_buffer), end_of_stream=True
                        )
                        if opus:
                            if self.segment_count < 10:  # 前10个片段直接发送
                                # 直接发送
                                self.tts_audio_queue.put(
                                    (SentenceType.MIDDLE, opus, None)
                                )
                                self.segment_count += 1
                            else:
                                # 后续片段缓存
                                opus_datas_cache.extend(opus)
                        self.pcm_buffer.clear()

                    # 如果不是前10个片段，发送缓存的数据
                    if self.segment_count >= 10 and opus_datas_cache:
                        self.tts_audio_queue.put(
                            (SentenceType.MIDDLE, opus_datas_cache, None)
                        )

                    # 如果是最后一段，输出音频获取完毕
                    if is_last:
                        self._process_before_stop_play_files()

        except Exception as e:
            logger.error(f"TTS请求异常: {e}")
            self.tts_audio_queue.put((SentenceType.LAST, [], None))

    def to_tts(self, text: str) -> list:
        """非流式TTS处理，用于测试及保存音频文件的场景

        Args:
            text: 要转换的文本

        Returns:
            list: 返回opus编码后的音频数据列表
        """
        start_time = time.time()
        text = MarkdownCleaner.clean_markdown(text)

        params = {
            "tts_text": text,
            "spk_id": self.voice,
            "frame_duration": 60,
            "stream": False,
            "target_sr": 16000,
            "audio_format": self.audio_format,
            "instruct_text": "请生成一段自然流畅的语音",
        }
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        try:
            with requests.get(
                self.api_url, params=params, headers=headers, timeout=5
            ) as response:
                if response.status_code != 200:
                    logger.error(
                        f"TTS请求失败: {response.status_code}, {response.text}"
                    )
                    return []

                logger.info(f"TTS请求成功: {text}, 耗时: {time.time() - start_time}秒")

                # 使用opus编码器处理PCM数据
                opus_datas = []
                pcm_data = response.content

                # 计算每帧的字节数
                frame_bytes = int(
                    self.opus_encoder.sample_rate
                    * self.opus_encoder.channels
                    * self.opus_encoder.frame_size_ms
                    / 1000
                    * 2
                )

                # 分帧处理PCM数据
                for i in range(0, len(pcm_data), frame_bytes):
                    frame = pcm_data[i : i + frame_bytes]
                    if len(frame) < frame_bytes:
                        # 最后一帧可能不足，用0填充
                        frame = frame + b"\x00" * (frame_bytes - len(frame))

                    opus = self.opus_encoder.encode_pcm_to_opus(
                        frame, end_of_stream=(i + frame_bytes >= len(pcm_data))
                    )
                    if opus:
                        opus_datas.extend(opus)

                return opus_datas

        except Exception as e:
            logger.error(f"TTS请求异常: {e}")
            return []
