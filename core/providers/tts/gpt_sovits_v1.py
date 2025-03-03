import os
import uuid
import json
import base64
import requests
from config.logger import setup_logging
from datetime import datetime
from core.providers.tts.base import TTSProviderBase
import urllib

TAG = __name__
logger = setup_logging()

class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.url = config.get("url")
        self.text_language = config.get("text_language", "中文")
        self.refer_wav_path = config.get("refer_wav_path")
        self.prompt_text = config.get("prompt_text")
        self.prompt_language = config.get("prompt_language", "zh")
        self.top_k = config.get("top_k", 5)
        self.top_p = config.get("top_p", 1)
        self.temperature = config.get("temperature", 1)
        self.cut_punc = config.get("cut_punc", "cut0")
        self.inp_refs = config.get("inp_refs", [])
        self.speed = config.get("speed", 1)

    def generate_filename(self, extension=".wav"):
        return os.path.join(self.output_file, f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}")

    async def text_to_speak(self, text, output_file):
        request_json = {
            "text": text,
            "refer_wav_path": self.refer_wav_path,
            "prompt_text": self.prompt_text,
            "prompt_language": self.prompt_language,
            "text_language": self.text_language,
            "cut_punc": self.cut_punc,
            "top_k": self.top_k,
            "top_p": self.top_p,
            "temperature": self.temperature,
            "speed": self.speed,
            "inp_refs": self.inp_refs
        }
        query_string = urllib.parse.urlencode(request_json, safe='[]')  
        url = f'{self.url}?{query_string}'  
        print(url)
        resp = requests.get(url, headers={'accept': 'application/json'}  )
        if resp.status_code == 200:
            with open(output_file, "wb") as file:
                file.write(resp.content)
        else:
            logger.bind(tag=TAG).error(f"GPT_SoVITS_V2 TTS请求失败: {resp.status_code} - {resp.text}")

