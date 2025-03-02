import os
import uuid
import base64
import requests
from datetime import datetime
from core.providers.tts.base import TTSProviderBase


class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.access_token = config.get("access_token")
        self.voice = config.get("voice", "zh_female_wanwanxiaohe_moon_bigtts")

        # self.api_url = "https://api.302.ai/doubao/tts_hd" 国外
        self.api_url = "https://api.302ai.cn/doubao/tts_hd" #国内中转
        self.header = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}"
        }

    def generate_filename(self, extension=".wav"):
        return os.path.join(self.output_file, f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}")

    async def text_to_speak(self, text, output_file):

        request_json = {
            "audio": {
                "voice_type": self.voice,
                "encoding": "wav",
                "speed_ratio": 1.0
            },
            "request": {
                "reqid": str(uuid.uuid4()),
                "text": text,
                "operation": "query"
            }
        }
        print("执行", text,request_json)
        try:
            resp = requests.post(self.api_url, json=request_json, headers=self.header)
            if resp.status_code == 200 and "data" in resp.json():
                data = resp.json()["data"]
                with open(output_file, "wb") as file_to_save:
                    file_to_save.write(base64.b64decode(data))
            else:
                raise Exception(f"{__name__} status_code: {resp.status_code} response: {resp.content}")
        except Exception as e:
            raise Exception(f"{__name__} error: {e}")
