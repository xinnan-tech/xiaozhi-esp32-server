import requests
from core.utils.util import check_model_key
from core.providers.tts.base import TTSProviderBase
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.api_key = config.get("api_key")
        self.model_name = config.get("model_name")
        self.output_dir = config.get("output_dir")
        self.host = config.get("host")
        if self.host is None:
            self.host = "ai-gateway.vei.volces.com"
        if self.output_dir is None:
            self.output_dir = "tmp/"
        self.delete_audio_file = delete_audio_file
        self.base_url = f"https://{self.host}/v1/audio/speech"

        if config.get("private_voice"):
            self.voice = config.get("private_voice")
        else:
            self.voice = config.get("voice", "alloy")
        self.audio_file_type = config.get("format", "wav")

        # 处理空字符串的情况
        speed = config.get("speed", "1.0")
        self.speed = float(speed) if speed else 1.0
        
        check_model_key("TTS", self.api_key)

    async def text_to_speak(self, text, output_file):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        data = {
            "model": self.model_name,
            "input": text,
            "voice": self.voice,
            "response_format": "wav",
            "speed": self.speed,
        }
        response = requests.post(self.base_url, json=data, headers=headers)
        if response.status_code == 200:
            if output_file:
                with open(output_file, "wb") as audio_file:
                    audio_file.write(response.content)
            else:
                return response.content
        else:
            raise Exception(
                f"OpenAI TTS请求失败: {response.status_code} - {response.text}"
            )
