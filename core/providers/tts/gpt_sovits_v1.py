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

    # async def text_to_speak(self, text, output_file):
    #     request_json = {
    #         "text": text,
    #         "refer_wav_path": "E:\\alearn\\GPT-SoVITS\\纳西妲\\0.wav",
    #         "prompt_text": "初次见面…_初次见面，我已经关注你很久了。我叫纳西妲，别看我像个孩子，我比任何一位大人都了解这个世界。所以，我可以用我的知识，换取你路上的见闻吗？",
    #         "prompt_language": "中文",
    #         "text_language": "中文",
    #         "cut_punc": "",
    #         "top_k": 15,
    #         "top_p": 1,
    #         "temperature": 1,
    #         "speed": 1,
    #         "inp_refs": []
    #     }

    #     resp = requests.get(self.url, json=request_json)
    #     if resp.status_code == 200:
    #         with open(output_file, "wb") as file:
    #             file.write(resp.content)
    #     else:
    #         logger.bind(tag=TAG).error(f"GPT_SoVITS_V2 TTS请求失败: {resp.status_code} - {resp.text}")

    """
    curl -X 'GET' \
  'http://127.0.0.1:9880/?refer_wav_path=E%3A%5Calearn%5CGPT-SoVITS%5C%E7%BA%B3%E8%A5%BF%E5%A6%B2%5C0.wav&prompt_text=%E5%88%9D%E6%AC%A1%E8%A7%81%E9%9D%A2%E2%80%A6_%E5%88%9D%E6%AC%A1%E8%A7%81%E9%9D%A2%EF%BC%8C%E6%88%91%E5%B7%B2%E7%BB%8F%E5%85%B3%E6%B3%A8%E4%BD%A0%E5%BE%88%E4%B9%85%E4%BA%86%E3%80%82%E6%88%91%E5%8F%AB%E7%BA%B3%E8%A5%BF%E5%A6%B2%EF%BC%8C%E5%88%AB%E7%9C%8B%E6%88%91%E5%83%8F%E4%B8%AA%E5%AD%A9%E5%AD%90%EF%BC%8C%E6%88%91%E6%AF%94%E4%BB%BB%E4%BD%95%E4%B8%80%E4%BD%8D%E5%A4%A7%E4%BA%BA%E9%83%BD%E4%BA%86%E8%A7%A3%E8%BF%99%E4%B8%AA%E4%B8%96%E7%95%8C%E3%80%82%E6%89%80%E4%BB%A5%EF%BC%8C%E6%88%91%E5%8F%AF%E4%BB%A5%E7%94%A8%E6%88%91%E7%9A%84%E7%9F%A5%E8%AF%86%EF%BC%8C%E6%8D%A2%E5%8F%96%E4%BD%A0%E8%B7%AF%E4%B8%8A%E7%9A%84%E8%A7%81%E9%97%BB%E5%90%97%EF%BC%9F&prompt_language=%E4%B8%AD%E6%96%87&text=%E4%BD%A0%E5%A5%BD&text_language=%E4%B8%AD%E6%96%87&top_k=15&top_p=1&temperature=1&speed=1' \
  -H 'accept: application/json'
    """
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

