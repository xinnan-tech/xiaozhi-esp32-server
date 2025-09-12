import uuid
import json
import hmac
import hashlib
import base64
import requests
from datetime import datetime
from core.providers.tts.base import TTSProviderBase
from config.logger import setup_logging
import time
import uuid
from urllib import parse

from dashscope.audio.tts_v2 import SpeechSynthesizer, AudioFormat
import dashscope
import os

TAG = __name__
logger = setup_logging()


class TTSProvider(TTSProviderBase):

    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)


        self.api_key = config.get("api_key")
        self.voice = config.get("private_voice")
        if self.voice.startswith("cosyvoice-v3-"):
            self.model = "cosyvoice-v3"
        elif self.voice.startswith("cosyvoice-v2-"):
            self.model = "cosyvoice-v2"
        else:
            self.model = "cosyvoice-v1"

    def generate_filename(self, extension=".wav"):
        return os.path.join(self.output_file,
                            f"tts-{__name__}{datetime.now().date()}@{uuid.uuid4().hex}{extension}")

    async def text_to_speak(self, text, output_file):
        try:
            # 设置 DashScope 的 API 密钥
            dashscope.api_key = self.api_key

            # 创建语音合成器实例，指定模型、声音和音频格式
            synthesizer = SpeechSynthesizer(
                model=self.model,
                voice=self.voice,
                format=AudioFormat.WAV_16000HZ_MONO_16BIT,
                # callback=callback
            )

            # 调用语音合成接口，获取音频数据
            audiodata = synthesizer.call(text)

            # 如果指定了输出文件，则将音频数据写入文件，并返回文件路径
            if output_file:
                with open(output_file, 'wb') as f:
                    f.write(audiodata)
                return output_file
            else:
                # 否则直接返回音频数据
                return audiodata
        except Exception as e:
            raise Exception(f"{__name__} error: {e}")
