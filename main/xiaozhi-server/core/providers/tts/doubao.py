import os
import uuid
import json
import base64
import requests
from datetime import datetime
from core.utils.util import check_model_key
from core.providers.tts.base import TTSProviderBase
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        if config.get("appid"):
            self.appid = int(config.get("appid"))
        else:
            self.appid = ""
        self.access_token = config.get("access_token")
        self.cluster = config.get("cluster")

        if config.get("private_voice"):
            self.voice = config.get("private_voice")
        else:
            self.voice = config.get("voice")

        # 处理空字符串的情况
        speed_ratio = config.get("speed_ratio", "1.0")
        volume_ratio = config.get("volume_ratio", "1.0")
        pitch_ratio = config.get("pitch_ratio", "1.0")

        self.speed_ratio = float(speed_ratio) if speed_ratio else 1.0
        self.volume_ratio = float(volume_ratio) if volume_ratio else 1.0
        self.pitch_ratio = float(pitch_ratio) if pitch_ratio else 1.0

        self.api_url = config.get("api_url")
        self.authorization = config.get("authorization")
        self.header = {"Authorization": f"{self.authorization}{self.access_token}"}
        check_model_key("TTS", self.access_token)

    def generate_filename(self, extension=".wav"):
        return os.path.join(
            self.output_file,
            f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}",
        )

    async def text_to_speak(self, text, output_file):
        request_json = {
            "app": {
                "appid": f"{self.appid}",
                "token": self.access_token,
                "cluster": self.cluster,
            },
            "user": {"uid": "1"},
            "audio": {
                "voice_type": self.voice,
                "encoding": "wav",
                "speed_ratio": self.speed_ratio,
                "volume_ratio": self.volume_ratio,
                "pitch_ratio": self.pitch_ratio,
            },
            "request": {
                "reqid": str(uuid.uuid4()),
                "text": text,
                "text_type": "plain",
                "operation": "query",
                "with_frontend": 1,
                "frontend_type": "unitTson",
            },
        }

        try:
            resp = requests.post(
                self.api_url, json.dumps(request_json), headers=self.header
            )
            if "data" in resp.json():
                data = resp.json()["data"]
                file_to_save = open(output_file, "wb")
                file_to_save.write(base64.b64decode(data))
            else:
                raise Exception(
                    f"{__name__} status_code: {resp.status_code} response: {resp.content}"
                )
        except Exception as e:
            raise Exception(f"{__name__} error: {e}")
