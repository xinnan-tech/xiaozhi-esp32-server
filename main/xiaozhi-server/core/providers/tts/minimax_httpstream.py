import os
import json
import time
import queue
import asyncio
import aiohttp
import requests
import traceback
from config.logger import setup_logging
from core.utils.tts import MarkdownCleaner
from core.utils.util import parse_string_to_list
from core.providers.tts.base import TTSProviderBase
from core.utils import opus_encoder_utils, textUtils
from core.providers.tts.dto.dto import SentenceType, ContentType

TAG = __name__
logger = setup_logging()


class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.group_id = config.get("group_id")
        self.api_key = config.get("api_key")
        self.model = config.get("model")
        if config.get("private_voice"):
            self.voice = config.get("private_voice")
        else:
            self.voice = config.get("voice_id")

        default_voice_setting = {
            "voice_id": "female-shaonv",
            "speed": 1,
            "vol": 1,
            "pitch": 0,
            "emotion": "happy",
        }
        default_pronunciation_dict = {"tone": ["处理/(chu3)(li3)", "危险/dangerous"]}
        defult_audio_setting = {
            "sample_rate": 16000,
            "format": "pcm",
            "channel": 1,
        }
        self.voice_setting = {
            **default_voice_setting,
            **config.get("voice_setting", {}),
        }
        self.pronunciation_dict = {
            **default_pronunciation_dict,
            **config.get("pronunciation_dict", {}),
        }
        self.audio_setting = {**defult_audio_setting, **config.get("audio_setting", {})}
        self.timber_weights = parse_string_to_list(config.get("timber_weights"))

        if self.voice:
            self.voice_setting["voice_id"] = self.voice

        self.host = "api.minimax.io"
        self.api_url = f"https://{self.host}/v1/t2a_v2"
        self.header = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        self.audio_file_type = defult_audio_setting.get("format", "pcm")

        self.opus_encoder = opus_encoder_utils.OpusEncoderUtils(
            sample_rate=24000, channels=1, frame_size_ms=60
        )

        # PCM缓冲区
        self.pcm_buffer = bytearray()

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
                    if message.content_file and os.path.exists(message.content_file):
                        # 先处理文件音频数据
                        self._process_audio_file_stream(message.content_file, callback=lambda audio_data: self.handle_audio_file(audio_data, message.content_detail))
                if message.sentence_type == SentenceType.LAST:
                    # 处理剩余的文本
                    self._process_remaining_text_stream(True)

            except queue.Empty:
                continue
            except Exception as e:
                logger.bind(tag=TAG).error(
                    f"处理TTS文本失败: {str(e)}, 类型: {type(e).__name__}, 堆栈: {traceback.format_exc()}"
                )

    def _process_remaining_text_stream(self, is_last=False):
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

    async def text_to_speak(self, text, is_last):
        """流式处理TTS音频，每句只推送一次音频列表"""
        payload = {
            "model": self.model,
            "text": text,
            "stream": True,
            "voice_setting": self.voice_setting,
            "pronunciation_dict": self.pronunciation_dict,
            "audio_setting": self.audio_setting,
        }

        if type(self.timber_weights) is list and len(self.timber_weights) > 0:
            payload["timber_weights"] = self.timber_weights
            payload["voice_setting"]["voice_id"] = ""

        frame_bytes = int(
            self.opus_encoder.sample_rate
            * self.opus_encoder.channels  # 1
            * self.opus_encoder.frame_size_ms
            / 1000
            * 2
        )  # 16-bit = 2 bytes
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    headers=self.header,
                    data=json.dumps(payload),
                    timeout=10,
                ) as resp:

                    if resp.status != 200:
                        logger.bind(tag=TAG).error(
                            f"TTS请求失败: {resp.status}, {await resp.text()}"
                        )
                        self.tts_audio_queue.put((SentenceType.LAST, [], None))
                        return

                    self.pcm_buffer.clear()
                    self.tts_audio_queue.put((SentenceType.FIRST, [], text))

                    # 处理音频流数据
                    buffer = b""
                    async for chunk in resp.content.iter_any():
                        if not chunk:
                            continue

                        buffer += chunk
                        while True:
                            # 查找数据块分隔符
                            header_pos = buffer.find(b"data: ")
                            if header_pos == -1:
                                break

                            end_pos = buffer.find(b"\n\n", header_pos)
                            if end_pos == -1:
                                break

                            # 提取单个完整JSON块
                            json_str = buffer[header_pos + 6 : end_pos].decode("utf-8")
                            buffer = buffer[end_pos + 2 :]

                            try:
                                data = json.loads(json_str)
                                status = data.get("data", {}).get("status", 1)
                                audio_hex = data.get("data", {}).get("audio")

                                # 仅处理status=1的有效音频块 忽略status=2的结束汇总块
                                if status == 1 and audio_hex:
                                    pcm_data = bytes.fromhex(audio_hex)
                                    self.pcm_buffer.extend(pcm_data)

                            except json.JSONDecodeError as e:
                                logger.bind(tag=TAG).error(f"JSON解析失败: {e}")
                                continue

                        while len(self.pcm_buffer) >= frame_bytes:
                            frame = bytes(self.pcm_buffer[:frame_bytes])
                            del self.pcm_buffer[:frame_bytes]

                            self.opus_encoder.encode_pcm_to_opus_stream(
                                frame, end_of_stream=False, callback=self.handle_opus
                            )

                    # flush 剩余不足一帧的数据
                    if self.pcm_buffer:
                        self.opus_encoder.encode_pcm_to_opus_stream(
                            bytes(self.pcm_buffer),
                            end_of_stream=True,
                            callback=self.handle_opus,
                        )
                        self.pcm_buffer.clear()

                    # 如果是最后一段，输出音频获取完毕
                    if is_last:
                        self._process_before_stop_play_files()

        except Exception as e:
            logger.bind(tag=TAG).error(f"TTS请求异常: {e}")
            self.tts_audio_queue.put((SentenceType.LAST, [], None))

    async def close(self):
        """资源清理"""
        await super().close()
        if hasattr(self, "opus_encoder"):
            self.opus_encoder.close()

    def to_tts(self, text: str) -> list:
        """非流式TTS处理，用于测试及保存音频文件的场景
        Args:
            text: 要转换的文本
        Returns:
            list: 返回opus编码后的音频数据列表
        """
        start_time = time.time()
        text = MarkdownCleaner.clean_markdown(text)

        payload = {
            "model": self.model,
            "text": text,
            "stream": True,
            "voice_setting": self.voice_setting,
            "pronunciation_dict": self.pronunciation_dict,
            "audio_setting": self.audio_setting,
        }

        if type(self.timber_weights) is list and len(self.timber_weights) > 0:
            payload["timber_weights"] = self.timber_weights
            payload["voice_setting"]["voice_id"] = ""

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        try:
            with requests.post(
                self.api_url, data=json.dumps(payload), headers=headers, timeout=5
            ) as response:
                if response.status_code != 200:
                    logger.bind(tag=TAG).error(
                        f"TTS请求失败: {response.status_code}, {response.text}"
                    )
                    return []

                logger.info(f"TTS请求成功: {text}, 耗时: {time.time() - start_time}秒")

                # 使用opus编码器处理PCM数据
                opus_datas = []
                full_content = response.content.decode('utf-8')
                pcm_data = bytearray()
                for data_block in full_content.split('\n\n'):
                    if not data_block.startswith('data: '):
                        continue

                    try:
                        json_str = data_block[6:]  # 去除'data: '前缀
                        data = json.loads(json_str)
                        if data.get('data', {}).get('status') == 1:
                            audio_hex = data['data']['audio']
                            pcm_data.extend(bytes.fromhex(audio_hex))
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.bind(tag=TAG).warning(f"无效数据块: {e}")
                        continue

                # 计算每帧的字节数
                frame_bytes = int(
                    self.opus_encoder.sample_rate
                    * self.opus_encoder.channels
                    * self.opus_encoder.frame_size_ms
                    / 1000
                    * 2
                )

                # 分帧处理合并后的PCM数据
                for i in range(0, len(pcm_data), frame_bytes):
                    frame = bytes(pcm_data[i:i+frame_bytes])
                    if len(frame) < frame_bytes:
                        frame += b"\x00" * (frame_bytes - len(frame))
 
                    self.opus_encoder.encode_pcm_to_opus_stream(
                        frame,
                        end_of_stream=(i + frame_bytes >= len(pcm_data)),
                        callback=lambda opus: opus_datas.append(opus)
                    )

                return opus_datas

        except Exception as e:
            logger.bind(tag=TAG).error(f"TTS请求异常: {e}")
            return []
