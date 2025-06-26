import os
import wave
import copy
import uuid
import queue
import asyncio
import traceback
import threading
import opuslib_next
from abc import ABC, abstractmethod
from config.logger import setup_logging
from typing import Optional, Tuple, List
from core.handle.receiveAudioHandle import startToChat
from core.handle.reportHandle import enqueue_asr_report
from core.utils.util import remove_punctuation_and_length
from core.handle.receiveAudioHandle import handleAudioMessage

TAG = __name__
logger = setup_logging()


class ASRProviderBase(ABC):
    def __init__(self):
        pass

    # 打开音频通道
    # 这里默认是非流式的处理方式
    # 流式处理方式请在子类中重写
    async def open_audio_channels(self, conn):
        # tts 消化线程
        conn.asr_priority_thread = threading.Thread(
            target=self.asr_text_priority_thread, args=(conn,), daemon=True
        )
        conn.asr_priority_thread.start()

    # 有序处理ASR音频
    def asr_text_priority_thread(self, conn):
        while not conn.stop_event.is_set():
            try:
                message = conn.asr_audio_queue.get(timeout=1)
                future = asyncio.run_coroutine_threadsafe(
                    handleAudioMessage(conn, message),
                    conn.loop,
                )
                future.result()
            except queue.Empty:
                continue
            except Exception as e:
                logger.bind(tag=TAG).error(
                    f"处理ASR文本失败: {str(e)}, 类型: {type(e).__name__}, 堆栈: {traceback.format_exc()}"
                )
                continue

    # 接收音频
    # 这里默认是非流式的处理方式
    # 流式处理方式请在子类中重写
    async def receive_audio(self, conn, audio, audio_have_voice):
        if conn.client_listen_mode == "auto" or conn.client_listen_mode == "realtime":
            have_voice = audio_have_voice
        else:
            have_voice = conn.client_have_voice
        # 如果本次没有声音，本段也没声音，就把声音丢弃了
        conn.asr_audio.append(audio)
        if have_voice == False and conn.client_have_voice == False:
            conn.asr_audio = conn.asr_audio[-10:]
            return

        # 如果本段有声音，且已经停止了
        if conn.client_voice_stop:
            asr_audio_task = copy.deepcopy(conn.asr_audio)
            conn.asr_audio.clear()

            # 音频太短了，无法识别
            conn.reset_vad_states()
            if len(asr_audio_task) > 15:
                await self.handle_voice_stop(conn, asr_audio_task)

    # 处理语音停止
    async def handle_voice_stop(self, conn, asr_audio_task):
        raw_text, _ = await self.speech_to_text(
            asr_audio_task, conn.session_id, conn.audio_format
        )  # 确保ASR模块返回原始文本
        conn.logger.bind(tag=TAG).info(f"识别文本: {raw_text}")
        text_len, _ = remove_punctuation_and_length(raw_text)
        self.stop_ws_connection()
        if text_len > 0:
            # 使用自定义模块进行上报
            await startToChat(conn, raw_text)
            enqueue_asr_report(conn, raw_text, asr_audio_task)

    def stop_ws_connection(self):
        pass

    def save_audio_to_file(self, pcm_data: List[bytes], session_id: str) -> str:
        """PCM数据保存为WAV文件"""
        module_name = __name__.split(".")[-1]
        file_name = f"asr_{module_name}_{session_id}_{uuid.uuid4()}.wav"
        file_path = os.path.join(self.output_dir, file_name)

        with wave.open(file_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 2 bytes = 16-bit
            wf.setframerate(16000)
            wf.writeframes(b"".join(pcm_data))

        return file_path

    @abstractmethod
    async def speech_to_text(
        self, opus_data: List[bytes], session_id: str, audio_format="opus"
    ) -> Tuple[Optional[str], Optional[str]]:
        """将语音数据转换为文本"""
        pass

    @staticmethod
    def decode_opus(opus_data: List[bytes]) -> bytes:
        """将Opus音频数据解码为PCM数据"""
        try:
            decoder = opuslib_next.Decoder(16000, 1)  # 16kHz, 单声道
            pcm_data = []
            buffer_size = 960  # 每次处理960个采样点

            for opus_packet in opus_data:
                try:
                    # 使用较小的缓冲区大小进行处理
                    pcm_frame = decoder.decode(opus_packet, buffer_size)
                    if pcm_frame:
                        pcm_data.append(pcm_frame)
                except opuslib_next.OpusError as e:
                    logger.bind(tag=TAG).warning(f"Opus解码错误，跳过当前数据包: {e}")
                    continue
                except Exception as e:
                    logger.bind(tag=TAG).error(f"音频处理错误: {e}", exc_info=True)
                    continue

            return pcm_data
        except Exception as e:
            logger.bind(tag=TAG).error(f"音频解码过程发生错误: {e}", exc_info=True)
            return []
