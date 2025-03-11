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
        self.text_lang = config.get("text_lang", "audo")
        self.ref_audio_path = config.get("ref_audio_path")
        self.prompt_lang = config.get("prompt_lang")
        self.prompt_text = config.get("prompt_text")
        self.top_k = config.get("top_k", 5)
        self.top_p = config.get("top_p", 1)
        self.temperature = config.get("temperature", 1)
        self.sample_steps = config.get("sample_steps", 16)
        self.media_type = config.get("media_type", "wav")
        self.streaming_mode = config.get("streaming_mode", False)
        self.threshold = config.get("threshold", 30)


    def generate_filename(self, extension=".wav"):
        return os.path.join(self.output_file, f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}")

    async def text_to_speak(self, text, output_file):
        request_params = {
            "text": text,
            "text_lang": self.text_lang,
            "ref_audio_path": self.ref_audio_path,
            "prompt_lang": self.prompt_lang,
            "prompt_text": self.prompt_text,
            "top_k": self.top_k,
            "top_p": self.top_p,
            "temperature": self.temperature,
            "sample_steps": self.sample_steps,
            "media_type": self.media_type,
            "streaming_mode": self.streaming_mode,
            "threshold": self.threshold,
        }

        resp = requests.get(self.url, params=request_params)
        if resp.status_code == 200:
            with open(output_file, "wb") as file:
                file.write(resp.content)
        else:
            logger.bind(tag=TAG).error(f"GPT_SoVITS_V3 TTS请求失败: {resp.status_code} - {resp.text}")
