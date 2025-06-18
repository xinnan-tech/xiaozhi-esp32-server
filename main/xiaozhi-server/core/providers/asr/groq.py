import os
import tempfile
import subprocess
import wave
from pathlib import Path
from groq import Groq, RateLimitError
from config.logger import setup_logging
from core.providers.asr.base import ASRProviderBase
from core.providers.asr.dto.dto import InterfaceType

TAG = __name__
logger = setup_logging()

class ASRProvider(ASRProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__()
        self.interface_type = InterfaceType.NON_STREAM
        self.api_key = config.get("api_key") or os.getenv("GROQ_API_KEY")
        self.model = config.get("model") or "distil-whisper-large-v3"
        self.delete_audio_file = delete_audio_file

    def preprocess_audio(self, pcm_data: bytes) -> Path:
        # Write PCM data to a valid WAV file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
            with wave.open(temp_wav, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 16-bit PCM
                wf.setframerate(16000)
                wf.writeframes(pcm_data)
            wav_path = Path(temp_wav.name)
        with tempfile.NamedTemporaryFile(suffix='.flac', delete=False) as temp_flac:
            flac_path = Path(temp_flac.name)
        # Convert to 16kHz mono FLAC
        subprocess.run([
            'ffmpeg', '-hide_banner', '-loglevel', 'error',
            '-i', str(wav_path),
            '-ar', '16000', '-ac', '1', '-c:a', 'flac', '-y', str(flac_path)
        ], check=True)
        wav_path.unlink(missing_ok=True)
        return flac_path

    async def speech_to_text(self, opus_data, session_id, audio_format="opus"):
        # Decode opus to PCM using base class method
        if audio_format == "pcm":
            pcm_data = b"".join(opus_data)
        else:
            pcm_data = b"".join(self.decode_opus(opus_data))
        flac_path = self.preprocess_audio(pcm_data)
        try:
            client = Groq(api_key=self.api_key)
            with open(flac_path, "rb") as f:
                result = client.audio.transcriptions.create(
                    file=("audio.flac", f, "audio/flac"),
                    model=self.model,
                    response_format="verbose_json"
                )
            # Handle both dict and object result
            if hasattr(result, "text"):
                text = result.text
            elif isinstance(result, dict):
                text = result.get("text", "")
            else:
                text = ""
            return text, None
        except Exception as e:
            logger.bind(tag=TAG).error(f"Groq ASR error: {e}")
            return "", None
        finally:
            flac_path.unlink(missing_ok=True)