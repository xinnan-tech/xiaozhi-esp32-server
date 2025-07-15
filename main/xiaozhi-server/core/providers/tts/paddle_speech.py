import base64
import aiohttp
from core.providers.tts.base import TTSProviderBase
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.url = config.get("url")
        self.spk_id = config.get("spk_id", 0)
        self.speed = config.get("speed", 1.0)
        self.volume = config.get("volume", 1.0)
        self.sample_rate = config.get("sample_rate", 0)
        self.save_path = config.get("save_path", "./streaming_tts.wav")

    async def text_to_speak(self, text, output_file):
        request_json = {
            "text": text,
            "spk_id": self.spk_id,
            "speed": self.speed,
            "volume": self.volume,
            "sample_rate": self.sample_rate,
            "save_path": self.save_path
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.url, json=request_json) as resp:
                    if resp.status == 200:
                        resp_json = await resp.json()
                        if resp_json.get("success"):
                            data = resp_json["result"]
                            audio_bytes = base64.b64decode(data["audio"])
                            if output_file:
                                with open(output_file, "wb") as file_to_save:
                                    file_to_save.write(audio_bytes)
                            else:
                                return audio_bytes
                        else:
                            raise Exception(f"Error: {resp_json.get('message', 'Unknown error')}")
                    else:
                        raise Exception(f"HTTP Error: {resp.status} - {await resp.text()}")
        except Exception as e:
            raise Exception(f"Error during TTS request: {e}")
