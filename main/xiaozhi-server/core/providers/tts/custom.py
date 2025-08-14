import os

import json

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

        self.method = config.get("method", "GET")

        self.headers = config.get("headers", {})

        self.format = config.get("format", "wav")

        self.audio_file_type = config.get("format", "wav")

        self.output_file = config.get("output_dir", "tmp/")

        self.params = config.get("params")

        if isinstance(self.params, str):

            try:

                self.params = json.loads(self.params)

            except json.JSONDecodeError:

                raise ValueError("Custom TTS configuration parameter error, unable to parse string as object")

        elif not isinstance(self.params, dict):

            raise TypeError("Custom TTS configuration parameter error, please refer to configuration instructions")

    def generate_filename(self):

        return os.path.join(self.output_file, f"tts-{datetime.now().date()}@{uuid.uuid4().hex}.{self.format}")

    async def text_to_speak(self, text, output_file):

        request_params = {}

        for k, v in self.params.items():

            if isinstance(v, str) and "{prompt_text}" in v:

                v = v.replace("{prompt_text}", text)

            request_params[k] = v

        if self.method.upper() == "POST":

            resp = requests.post(self.url, json=request_params, headers=self.headers)

        else:

            resp = requests.get(self.url, params=request_params, headers=self.headers)

        if resp.status_code == 200:

            if output_file:

                with open(output_file, "wb") as file:

                    file.write(resp.content)

            else:

                return resp.content

        else:

            error_msg = f"Custom TTS request failed: {resp.status_code} - {resp.text}"

            logger.bind(tag=TAG).error(error_msg)

            raise Exception(error_msg) # Throw exception for caller to catch