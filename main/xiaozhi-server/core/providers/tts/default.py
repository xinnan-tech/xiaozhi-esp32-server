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
        """生成唯一的音频文件名"""
        import uuid

        return os.path.join(self.output_dir, f"{uuid.uuid4()}.wav")

    async def text_to_speak(self, text, output_file):
        logger.bind(tag=TAG).error(f"无法实例化 TTS 服务，请检查配置")
