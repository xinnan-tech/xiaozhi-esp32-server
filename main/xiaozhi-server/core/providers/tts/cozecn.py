import requests
from core.providers.tts.base import TTSProviderBase


class TTSProvider(TTSProviderBase):
    TTS_PARAM_CONFIG = [
        ("speed", "speed", 0.5, 2, 1, lambda v: round(float(v), 1)),
        ("loudness_rate", "loudness_rate", -50, 100, 0, int),
    ]

    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.model = config.get("model")
        self.access_token = config.get("access_token")
        if config.get("private_voice"):
            self.voice = config.get("private_voice")
        else:
            self.voice = config.get("voice")
        self.audio_file_type = config.get("response_format", "wav")
        self.host = "api.coze.cn"
        self.api_url = f"https://{self.host}/v1/audio/speech"

        # 音频参数配置
        speed = config.get("speed", "0")
        self.speed = int(speed) if speed else 0

        loudness_rate = config.get("loudness_rate", "0")
        self.loudness_rate = int(loudness_rate) if loudness_rate else 0

        # 应用百分比调整（如果存在），否则使用公有化配置
        self._apply_percentage_params(config)

    async def text_to_speak(self, text, output_file):
        request_json = {
            "model": self.model,
            "input": text,
            "voice_id": self.voice,
            "response_format": self.audio_file_type,
            "sample_rate": self.conn.sample_rate,
            "speed": self.speed,
            "loudness_rate": self.loudness_rate,
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
            if output_file:
                with open(output_file, "wb") as file_to_save:
                    file_to_save.write(data)
            else:
                return data
        except Exception as e:
            raise Exception(f"{__name__} error: {e}")
