import os
import json
import time
from typing import Optional, Tuple, List
from .base import ASRProviderBase
from config.logger import setup_logging
from config.config_loader import get_project_dir
from core.providers.asr.dto.dto import InterfaceType
import vosk

TAG = __name__
logger = setup_logging()

class ASRProvider(ASRProviderBase):
    def __init__(self, config: dict, delete_audio_file: bool = True):
        super().__init__()
        self.interface_type = InterfaceType.LOCAL
        self.model_path = self._resolve_model_path(config.get("model_path"))
        self.output_dir = config.get("output_dir", "tmp/")
        self.delete_audio_file = delete_audio_file
        
        # Initialize the VOSK model.
        self.model = None
        self.recognizer = None
        self._load_model()
        
        # Ensure the output directory exists.
        os.makedirs(self.output_dir, exist_ok=True)

    def _resolve_model_path(self, model_path: Optional[str]) -> str:
        """Resolve VOSK model paths consistently for local and Docker deployments."""
        default_relative_path = "models/vosk/vosk-model-en-us-0.22"
        raw_path = (model_path or "").strip() or default_relative_path
        if os.path.isabs(raw_path):
            return raw_path

        project_path = os.path.join(get_project_dir(), raw_path)
        if os.path.exists(project_path):
            return project_path

        # Fall back to the runtime CWD path so local one-off executions still work
        # even if the project root detection differs.
        return os.path.abspath(raw_path)

    def _load_model(self):
        """Load the VOSK model."""
        try:
            if not os.path.exists(self.model_path):
                raise FileNotFoundError(
                    f"VOSK model path does not exist: {self.model_path}"
                )
                
            logger.bind(tag=TAG).info(f"Loading VOSK model: {self.model_path}")
            self.model = vosk.Model(self.model_path)

            # Initialize the recognizer. VOSK expects 16 kHz input.
            self.recognizer = vosk.KaldiRecognizer(self.model, 16000)

            logger.bind(tag=TAG).info("VOSK model loaded successfully")
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to load VOSK model: {e}")
            raise

    async def speech_to_text(
        self, opus_data: List[bytes], session_id: str, artifacts=None
    ) -> Tuple[Optional[str], Optional[str]]:
        """Convert speech data into text."""
        try:
            # Make sure the model is available.
            if not self.model:
                logger.bind(tag=TAG).error(
                    "VOSK model is not loaded; recognition cannot continue"
                )
                return "", None
            
            if artifacts is None:
                return "", None
            if not artifacts.pcm_bytes:
                logger.bind(tag=TAG).warning("Combined PCM data is empty")
                return "", None

            start_time = time.time()
            
            
            # Run recognition. VOSK recommends chunks around 2000 bytes.
            chunk_size = 2000
            text_result = ""
            
            for i in range(0, len(artifacts.pcm_bytes), chunk_size):
                chunk = artifacts.pcm_bytes[i:i+chunk_size]
                if self.recognizer.AcceptWaveform(chunk):
                    result = json.loads(self.recognizer.Result())
                    text = result.get('text', '')
                    if text:
                        text_result += text + " "
            
            # Fetch the final recognition result.
            final_result = json.loads(self.recognizer.FinalResult())
            final_text = final_result.get('text', '')
            if final_text:
                text_result += final_text
            
            logger.bind(tag=TAG).debug(
                f"VOSK speech recognition time: {time.time() - start_time:.3f}s | Result: {text_result.strip()}"
            )
            
            return text_result.strip(), artifacts.file_path
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"VOSK speech recognition failed: {e}")
            return "", None
