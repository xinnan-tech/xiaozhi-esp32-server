import os
import uuid
import edge_tts
import edge_tts.communicate  # explicit import; WSS_URL is reassigned on this module below
from datetime import datetime
from core.providers.tts.base import TTSProviderBase
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()

# Since 2026-10 Microsoft returns 403 for the legacy consumer endpoint, and
# edge-tts 7.2.8 still talks to speech.platform.bing.com, which no longer works.
# Upstream PR rany2/edge-tts#491 fixes it by switching to api.msedgeservices.com,
# but 7.2.8 is still the newest release on PyPI, so temporarily override WSS_URL.
# TODO(7.2.9): remove this monkey patch once edge-tts >= 7.2.9 is available.
_NEW_WSS_URL = (
    "wss://api.msedgeservices.com/tts/cognitiveservices/websocket/v1"
    f"?Ocp-Apim-Subscription-Key={edge_tts.constants.TRUSTED_CLIENT_TOKEN}"
)
# Line 35 of communicate.py, `from .constants import WSS_URL`, copies WSS_URL
# into a module-local name at import time, so patching only
# edge_tts.constants.WSS_URL has no effect. __stream() resolves WSS_URL via LEGB
# to edge_tts.communicate.WSS_URL, so both names must be patched here.
edge_tts.constants.WSS_URL = _NEW_WSS_URL
edge_tts.communicate.WSS_URL = _NEW_WSS_URL


class TTSProvider(TTSProviderBase):
    TTS_PARAM_CONFIG = [
        ("ttsVolume", "volume", 0, 100, 50, int),
        ("ttsRate", "speech_rate", -100, 100, 0, int),
        ("ttsPitch", "pitch_rate", -100, 100, 0, int),
    ]

    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        if config.get("private_voice"):
            self.voice = config.get("private_voice")
        else:
            self.voice = config.get("voice")
        self.audio_file_type = config.get("format", "mp3")

        volume = config.get("volume", "50")
        self.volume = int(volume) if volume else 50

        speech_rate = config.get("rate", "0")
        self.speech_rate = int(speech_rate) if speech_rate else 0

        pitch_rate = config.get("pitch", "0")
        self.pitch_rate = int(pitch_rate) if pitch_rate else 0

        # Apply percentage-adjusted params (ttsVolume/ttsRate/ttsPitch)
        # coming from the manager console, per TTS_PARAM_CONFIG above.
        self._apply_percentage_params(config)

        self.edge_rate = f"{self.speech_rate:+}%"
        self.edge_volume = f"{self.volume:+}%"
        self.edge_pitch = f"{self.pitch_rate:+}Hz"

        logger.debug(
            f"Edge TTS parameters initialized: voice={self.voice}, format={self.audio_file_type}, "
            f"rate={self.edge_rate}, volume={self.edge_volume}, pitch={self.edge_pitch}"
        )

    def generate_filename(self, extension=".mp3"):
        return os.path.join(
            self.output_file,
            f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}",
        )

    async def text_to_speak(self, text, output_file):
        logger.bind(tag=TAG).debug(f"Sending Edge TTS request with voice: {self.voice}, text length: {len(text)}")
        
        try:
            logger.bind(tag=TAG).debug(f"Creating Edge TTS communicate object")
            communicate = edge_tts.Communicate(
                text,
                voice=self.voice,
                rate=self.edge_rate,
                volume=self.edge_volume,
                pitch=self.edge_pitch,
            )
            
            if output_file:
                logger.bind(tag=TAG).debug(f"Writing Edge TTS audio to file: {output_file}")
                # Ensure directory exists and create empty file
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
                with open(output_file, "wb") as f:
                    pass

                # Stream write audio data
                logger.bind(tag=TAG).debug(f"Streaming Edge TTS audio data to file")
                with open(output_file, "ab") as f:  # Change to append mode to avoid overwriting
                    chunk_count = 0
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":  # Only process audio data chunks
                            f.write(chunk["data"])
                            chunk_count += 1
                    logger.bind(tag=TAG).debug(f"Successfully wrote Edge TTS audio file: {output_file}, processed {chunk_count} audio chunks")
            else:
                logger.bind(tag=TAG).debug(f"Collecting Edge TTS audio data in memory")
                # Return audio binary data
                audio_bytes = b""
                chunk_count = 0
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_bytes += chunk["data"]
                        chunk_count += 1
                logger.bind(tag=TAG).debug(f"Successfully collected Edge TTS audio data, size: {len(audio_bytes)} bytes, processed {chunk_count} audio chunks")
                return audio_bytes
                
        except Exception as e:
            logger.bind(tag=TAG).error(f"Edge TTS request failed: {e}")
            error_msg = f"Edge TTS request failed: {e}"
            raise Exception(error_msg)  # Throw exception for caller to catch