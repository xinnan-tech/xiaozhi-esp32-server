import os

from config.logger import setup_logging

from core.providers.tts.base import TTSProviderBase

TAG = __name__

logger = setup_logging()


class DefaultTTS(TTSProviderBase):

    def __init__(self, config, delete_audio_file=True):

        super().__init__(config, delete_audio_file)

        self.output_dir = config.get("output_dir", "output")

        if not os.path.exists(self.output_dir):

            os.makedirs(self.output_dir)

    def generate_filename(self):
        """Generate unique audio filename"""

        import uuid

        return os.path.join(self.output_dir, f"{uuid.uuid4()}.wav")

    async def text_to_speak(self, text, output_file):

        logger.bind(tag=TAG).error(
            f"Unable to instantiate TTS service, please check configuration")
