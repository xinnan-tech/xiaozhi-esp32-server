import os
from typing import Optional
from deepgram import DeepgramClient
from config.logger import setup_logging
from core.providers.tts.base import TTSProviderBase
from core.providers.tts.dto.dto import InterfaceType

TAG = __name__
logger = setup_logging()


class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.interface_type = InterfaceType.SINGLE_STREAM
        
        # Deepgram configuration
        self.api_key = config.get("api_key") or os.environ.get("DEEPGRAM_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Deepgram API key is required. "
                "Provide via api_key in config or set DEEPGRAM_API_KEY environment variable"
            )

        self.model = config.get("model", "aura-2-thalia-en") or os.environ.get("DEEPGRAM_MODEL")  # Default voice model
        self.encoding = config.get("encoding", "linear16")  # PCM format
        self.sample_rate = config.get("sample_rate", 16000)  # Match client sample rate     
        self.container = config.get("container", "none")  # Raw audio
        self.audio_file_type = "pcm"
        
        # Initialize Deepgram client
        self.client = DeepgramClient(api_key=self.api_key)
        
        logger.bind(tag=TAG).info(
            f"Deepgram TTS initialized: model={self.model}, "
            f"sample_rate={self.sample_rate}, encoding={self.encoding}"
        )

    async def text_to_speech(self, text: str, output_file: Optional[str] = None) -> Optional[bytes]:
        try:
            audio_stream = self.client.speak.v1.audio.generate(
                text=text,
                model=self.model,
                encoding = self.encoding,
                sample_rate = self.sample_rate,
                container = self.container,
            )

            if output_file:
                with open(output_file, 'wb') as f:
                    for chunk in audio_stream:
                        f.write(chunk)
            else:
                audio_bytes = b""
                for chunk in audio_stream:
                    audio_bytes += chunk["data"]
                return audio_bytes

        except Exception as e:
            logger.bind(tag=TAG).error(f"Deepgram TTS failed: {e}", exc_info=True)
            raise

    async def close(self):
        """Resource cleanup"""
        pass

