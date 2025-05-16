import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
import os
import uuid
from typing import Optional, Tuple, List
import wave
import opuslib_next

from aip import AipSpeech
from core.providers.asr.base import ASRProviderBase
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


class ASRProvider(ASRProviderBase):
    def __init__(self, config: dict, delete_audio_file: bool = True):
        super().__init__()
        self.app_id = config.get("app_id")
        self.api_key = config.get("api_key")
        self.secret_key = config.get("secret_key")

        dev_pid = config.get("dev_pid", "1537")
        self.dev_pid = int(dev_pid) if dev_pid else 1537

        self.output_dir = config.get("output_dir")
        self.delete_audio_file = delete_audio_file

        self.client = AipSpeech(str(self.app_id), self.api_key, self.secret_key)

        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)

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

    async def speech_to_text(
        self, opus_data: List[bytes], session_id: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """将语音数据转换为文本"""
        if not opus_data:
            logger.bind(tag=TAG).warning("音频数据为空！")
            return None, None

        file_path = None
        try:
            # 检查配置是否已设置
            if not self.app_id or not self.api_key or not self.secret_key:
                logger.bind(tag=TAG).error("百度语音识别配置未设置，无法进行识别")
                return None, file_path

            # 将Opus音频数据解码为PCM
            if self.audio_format == "pcm":
                pcm_data = opus_data
            else:
                pcm_data = self.decode_opus(opus_data)
            combined_pcm_data = b"".join(pcm_data)

            # 判断是否保存为WAV文件
            if self.delete_audio_file:
                pass
            else:
                self.save_audio_to_file(pcm_data, session_id)

            start_time = time.time()
            # 识别本地文件
            result = self.client.asr(
                combined_pcm_data,
                "pcm",
                16000,
                {
                    "dev_pid": str(self.dev_pid),
                },
            )

            if result and result["err_no"] == 0:
                logger.bind(tag=TAG).debug(
                    f"百度语音识别耗时: {time.time() - start_time:.3f}s | 结果: {result}"
                )
                result = result["result"][0]
                return result, file_path
            else:
                raise Exception(
                    f"百度语音识别失败，错误码: {result['err_no']}，错误信息: {result['err_msg']}"
                )
                return None, file_path

        except Exception as e:
            logger.bind(tag=TAG).error(f"处理音频时发生错误！{e}", exc_info=True)
            return None, file_path
