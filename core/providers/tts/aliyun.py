import os
import uuid
import json
import requests
from datetime import datetime
from core.providers.tts.base import TTSProviderBase

import http.client
import urllib.parse


class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.appkey = config.get("appkey")
        self.token = config.get("token")
        self.format = config.get("format", "wav")
        self.sample_rate = config.get("sample_rate", 16000)
        self.voice = config.get("voice", "xiaoyun")
        self.volume = config.get("volume", 50)
        self.speech_rate = config.get("speech_rate", 0)
        self.pitch_rate = config.get("pitch_rate", 0)

        self.host = config.get("host", "nls-gateway-cn-shanghai.aliyuncs.com")
        self.api_url = f"https://{self.host}/stream/v1/tts"
        self.header = {
            "Content-Type": "application/json"
        }

    def generate_filename(self, extension=".wav"):
        return os.path.join(self.output_file, f"tts-{__name__}{datetime.now().date()}@{uuid.uuid4().hex}{extension}")

    async def text_to_speak(self, text, output_file):
        request_json = {
            "appkey": self.appkey,
            "token": self.token,
            "text": text,
            "format": self.format,
            "sample_rate": self.sample_rate,
            "voice": self.voice,
            "volume": self.volume,
            "speech_rate": self.speech_rate,
            "pitch_rate": self.pitch_rate
        }

        print(self.api_url, json.dumps(request_json, ensure_ascii=False))
        try:
            resp = requests.post(self.api_url, json.dumps(request_json), headers=self.header)
            # 检查返回请求数据的mime类型是否是audio/***，是则保存到指定路径下；返回的是binary格式的
            if resp.headers['Content-Type'].startswith('audio/'):
                with open(output_file, 'wb') as f:
                    f.write(resp.content)
                return output_file
            else:
                raise Exception(f"{__name__} status_code: {resp.status_code} response: {resp.content}")
        except Exception as e:
            raise Exception(f"{__name__} error: {e}")
