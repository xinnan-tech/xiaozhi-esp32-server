import os
import uuid
import json
import emoji
import requests
from datetime import datetime
from core.providers.tts.base import TTSProviderBase

class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        
        self.host = config.get("host")
        self.apikey = config.get("apikey")
        self.voice = config.get("voice", "zh-CN-XiaoxiaoNeural")
        self.api_url = f"http://{self.host}/v1/audio/speech"
        self.header = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.apikey}"
        }

    def clean_emojis(self, text):
        return emoji.replace_emoji(text, '')

    def generate_filename(self, extension=".mp3"):
        return os.path.join(self.output_file, f"tts-{__name__}{datetime.now().date()}@{uuid.uuid4().hex}{extension}")

    async def text_to_speak(self, text, output_file):
        request_json = {
            "input": self.clean_emojis(text),
            "voice": self.voice
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
