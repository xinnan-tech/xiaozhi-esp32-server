import os
import uuid
import requests
from datetime import datetime
from core.providers.tts.base import TTSProviderBase
import json

class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.model = config.get("model")
        self.access_token = config.get("access_token")
        self.voice = config.get("voice")
        self.response_format = config.get("response_format")
        self.sample_rate = config.get("sample_rate")
        self.speed = config.get("speed")
        self.gain = config.get("gain")

        self.host = "tts.linkerai.top"
        self.api_url = f"https://{self.host}/tts"

    def generate_filename(self, extension=".wav"):
        return os.path.join(self.output_file, f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}")

    async def text_to_speak(self, text, output_file):
        params = {
            "tts_text": text,
            "spk_id": self.voice,
            "frame_durition": 60,
            "stream": True,  
            "target_sr": self.sample_rate,
            "audio_format":"opus",
            "instruct_text":""
        }
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        with open(output_file,'w') as f:
            f.write('%s\n'%(json.dumps(params)))
            f.write('%s'%(json.dumps(headers)))

    def yield_data(self,params,headers):   
        response = requests.get(self.api_url, headers=headers, params=params, stream=True)
        if response.status_code == 200:
            for chunk in response.iter_content(chunk_size=None):
                if chunk:  
                    yield chunk
        else:
            print(f"请求失败，状态码: {response.status_code}")
            print(f"错误信息: {response.text}")

    def audio_to_opus_data(self, audio_file_path):
        duration = 100
        code = []
        with open(audio_file_path,encoding='utf-8') as f:
            for line in f.readlines():
                code.append(json.dumps(line))
        params = code[0]
        headers = code[1]

        return self.yield_data(params=params,headers=headers),duration
