import os
import uuid
import json
import base64
import requests
from datetime import datetime
from core.providers.tts.base import TTSProviderBase


class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.model = config.get("model")
        self.access_token = config.get("access_token")
        self.voice = config.get("voice")
        self.response_format = config.get("response_format")

        self.host = "api.coze.cn"
        self.api_url = f"https://{self.host}/v1/audio/speech"

    def generate_filename(self, extension=".wav"):
        return os.path.join(self.output_file, f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}")

    async def text_to_speak(self, text, output_file):
        request_json = {
            "model": self.model,
            "input": text,
            "voice_id": self.voice,
            "response_format": self.response_format,
        }
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        response = requests.request("POST", self.api_url, json=request_json, headers=headers)
        data = response.content
        file_to_save = open(output_file, "wb")
        file_to_save.write(data)
