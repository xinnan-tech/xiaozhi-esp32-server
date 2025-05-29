import requests
from core.providers.tts.base import TTSProviderBase


class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.model = config.get("model")
        self.access_token = config.get("access_token")
        if config.get("private_voice"):
            self.voice = config.get("private_voice")
        else:
            self.voice = config.get("voice")
        self.response_format = config.get("response_format")

        self.host = "api.coze.cn"
        self.api_url = f"https://{self.host}/v1/audio/speech"

    async def text_to_speak(self, text, output_file):
        request_json = {
            "model": self.model,
            "input": text,
            "voice_id": self.voice,
            "response_format": self.response_format,
        }
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.request(
                "POST", self.api_url, json=request_json, headers=headers
            )
            data = response.content
            file_to_save = open(output_file, "wb")
            file_to_save.write(data)
        except Exception as e:
            raise Exception(f"{__name__} error: {e}")
