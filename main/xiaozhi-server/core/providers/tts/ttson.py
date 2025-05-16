import os
import uuid
import json
import requests
import shutil
from datetime import datetime
from core.providers.tts.base import TTSProviderBase
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.url = config.get(
            "url",
            "https://u95167-bd74-2aef8085.westx.seetacloud.com:8443/flashsummary/tts?token=",
        )
        if config.get("private_voice"):
            self.voice_id = int(config.get("private_voice"))
        else:
            self.voice_id = int(config.get("voice_id", 1695))
        self.token = config.get("token")
        self.to_lang = config.get("to_lang")
        self.volume_change_dB = int(config.get("volume_change_dB", 0))
        self.speed_factor = int(config.get("speed_factor", 1))
        self.stream = str(config.get("stream", False)).lower() in ("true", "1", "yes")
        self.output_file = config.get("output_dir")
        self.pitch_factor = int(config.get("pitch_factor", 0))
        self.format = config.get("format", "mp3")
        self.emotion = int(config.get("emotion", 1))
        self.header = {"Content-Type": "application/json"}

    def generate_filename(self, extension=".mp3"):
        return os.path.join(
            self.output_file,
            f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}",
        )

    async def text_to_speak(self, text, output_file):
        url = f"{self.url}{self.token}"
        result = "firefly"
        payload = json.dumps(
            {
                "to_lang": self.to_lang,
                "text": text,
                "emotion": self.emotion,
                "format": self.format,
                "volume_change_dB": self.volume_change_dB,
                "voice_id": self.voice_id,
                "pitch_factor": self.pitch_factor,
                "speed_factor": self.speed_factor,
                "token": self.token,
            }
        )

        resp = requests.request("POST", url, data=payload)
        if resp.status_code != 200:
            logger.bind(tag=TAG).error(f"TTSON 请求失败: {resp.text}")
            raise Exception(f"{__name__}: TTS请求失败")
        resp_json = resp.json()
        try:
            result = (
                resp_json["url"]
                + ":"
                + str(resp_json["port"])
                + "/flashsummary/retrieveFileData?stream=True&token="
                + self.token
                + "&voice_audio_path="
                + resp_json["voice_path"]
            )

            audio_content = requests.get(result)
            with open(output_file, "wb") as f:
                f.write(audio_content.content)
                return True
            voice_path = resp_json.get("voice_path")
            des_path = output_file
            shutil.move(voice_path, des_path)

        except Exception as e:
            print("error:", e)
            raise Exception(f"{__name__}: TTS请求失败")