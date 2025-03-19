import os
import uuid
import requests
from config.logger import setup_logging
from datetime import datetime
from core.providers.tts.base import TTSProviderBase

TAG = __name__
logger = setup_logging()

class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.url = config.get("url")
        self.headers = config.get("headers", {})
        self.params = config.get("params")
        self.format = config.get("format", "wav")
        self.output_file = config.get("output_dir", "tmp/")

    def generate_filename(self):
        return os.path.join(self.output_file, f"tts-{datetime.now().date()}@{uuid.uuid4().hex}.{self.format}")

    async def text_to_speak(self, text, output_file):
        request_params = {}
        for k, v in self.params.items():
            if isinstance(v, str) and "{prompt_text}" in v:
                v = v.replace("{prompt_text}", text)
            request_params[k] = v

        resp = requests.get(self.url, params=request_params, headers=self.headers)
        if resp.status_code == 200:
            with open(output_file, "wb") as file:
                file.write(resp.content)
        else:
            logger.bind(tag=TAG).error(f"Custom TTS请求失败: {resp.status_code} - {resp.text}")
