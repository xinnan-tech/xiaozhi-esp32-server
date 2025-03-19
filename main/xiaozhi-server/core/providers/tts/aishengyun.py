import os
import uuid
import json
import base64
import requests
import websockets
from datetime import datetime
#from core.utils.util import check_model_key
from core.providers.tts.base import TTSProviderBase


class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.access_token = config.get("access_token")
        self.voice = config.get("voice")
        self.model_id = config.get("model_id")
        self.api_url = config.get("api_url")
        self.language = config.get("language")
        self.response_format = config.get("response_format")
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    def generate_filename(self, extension=".wav"):
        return os.path.join(self.output_file, f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}")

    async def text_to_speak(self, text, output_file):
        request_json = {
            "model_id": self.model_id,
            "voice": {
                "mode": "id",
                "id": self.voice
            },
            "output_format": {
                "container": self.response_format,
                "encoding": "pcm_s16le",
                "sample_rate": 16000
            },
            "language": self.language,
            "transcript": text
        }

        try:
            resp = requests.post(self.api_url, json.dumps(request_json), headers=self.headers)
            #file_name = resp.headers["content-disposition"].split("filename=")[1]
            with open(output_file, "wb") as file:
                file.write(resp.content)
        except Exception as e:
            raise Exception(f"{__name__} error: {e}")

async def main():
    from config.settings import load_config, check_config_file
    from core.utils import tts
    #check_config_file()
    config = load_config()
    #print(config)
    instance = tts.create_instance(
        config["selected_module"]["TTS"]
        if not 'type' in config["TTS"][config["selected_module"]["TTS"]]
        else
        config["TTS"][config["selected_module"]["TTS"]]["type"],
        config["TTS"][config["selected_module"]["TTS"]],
        config["delete_audio"]
    )
    file = instance.generate_filename()
    print(file)
    await instance.text_to_speak("你好", file)
    
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
    