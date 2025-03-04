import os
import uuid
import edge_tts
from datetime import datetime
from core.providers.tts.base import TTSProviderBase


class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.voice = config.get("voice")

    def generate_filename(self, extension=".mp3"):
        return os.path.join(self.output_file, f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}")

    async def text_to_speak(self, text, output_file):
        communicate = edge_tts.Communicate(text, voice=self.voice)  # Use your preferred voice
        await communicate.save(output_file)
