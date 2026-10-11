import time
import os
import io
import wave
import uuid
import json
import asyncio
import torch
import whisper
from config.logger import setup_logging
from typing import Optional, Tuple, List
from core.providers.asr.dto.dto import InterfaceType
from core.providers.asr.base import ASRProviderBase

TAG = __name__
logger = setup_logging()


class ASRProvider(ASRProviderBase):
    def __init__(self, config: dict, delete_audio_file: bool):
        self.interface_type = InterfaceType.NON_STREAM
        self.model_name = config.get("model_name", "base")
        self.output_dir = config.get("output_dir")
        self.device = config.get("device", "auto")  # auto, cpu, cuda
        lang = config.get("language")
        if isinstance(lang, str) and lang.strip() == "":
            lang = None
        self.language = lang
        self.delete_audio_file = delete_audio_file
        
        # Initialize Whisper model
        self._initialize_model()

        logger.debug(
            f"Whisper ASR parameters initialized: model={self.model_name}, device={self.device}, "
            f"language={self.language or 'auto-detect'}, output_dir={self.output_dir}, delete_audio_file={self.delete_audio_file}"
        )

        os.makedirs(self.output_dir, exist_ok=True)

    def _initialize_model(self):
        """Initialize the Whisper model"""
        try:
            start_time = time.time()
            
            # Determine device
            if self.device == "auto":
                if torch.cuda.is_available():
                    self.device = "cuda"
                    logger.bind(tag=TAG).info("CUDA available, using GPU for Whisper")
                else:
                    self.device = "cpu"
                    logger.bind(tag=TAG).info("CUDA not available, using CPU for Whisper")
            
            # Load Whisper model
            logger.bind(tag=TAG).info(f"Loading Whisper model: {self.model_name} on {self.device}")
            self.model = whisper.load_model(self.model_name, device=self.device)
            
            load_time = time.time() - start_time
            logger.bind(tag=TAG).info(f"Whisper model loaded successfully in {load_time:.2f}s")
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to initialize Whisper model: {e}")
            raise

    async def speech_to_text(
        self,
        opus_data: List[bytes],
        session_id: str,
        audio_format="opus",
        artifacts=None,
    ) -> Tuple[Optional[str], Optional[str]]:
        logger.bind(tag=TAG).debug(f"Processing Whisper ASR request, session_id: {session_id}, audio_format: {audio_format}")
        
        file_path = None
        try:
            start_time = time.time()
            
            # Decode audio data
            if audio_format == "pcm":
                pcm_data = opus_data
                logger.bind(tag=TAG).debug(f"Using PCM data directly, length: {len(opus_data)}")
            else:
                logger.bind(tag=TAG).debug(f"Decoding Opus data to PCM")
                pcm_data = self.decode_opus(opus_data)
                logger.bind(tag=TAG).debug(f"Decoded PCM data length: {len(pcm_data) if pcm_data else 0}")
            
            # Save audio to file for Whisper processing
            file_path = self.save_audio_to_file(pcm_data, session_id)
            logger.bind(tag=TAG).debug(f"Audio file saved: {file_path}")

            # Process with Whisper
            decode_start_time = time.time()
            
            # openai-whisper: model.transcribe(audio, **decode_options) — same as whisper.transcribe(model, audio, ...)
            # See https://github.com/openai/whisper/blob/main/whisper/transcribe.py
            # - language: omit or None → auto-detect; must be a LANGUAGES code or TO_LANGUAGE_CODE name (we normalize)
            # - task: "transcribe" | "translate"
            # - fp16: True on CUDA; False on CPU (upstream also downgrades fp16 on CPU if mis-set)
            # Do not pass verbose=False: transcribe uses disable=(verbose is not False), so False *enables* tqdm.
            transcribe_options = {
                "task": "transcribe",
                "fp16": self.device == "cuda",
            }
            if self.language:
                transcribe_options["language"] = self.language

            transcribe_options = {k: v for k, v in transcribe_options.items() if v is not None}
            
            logger.bind(tag=TAG).debug(f"Starting Whisper transcription with options: {transcribe_options}")
            
            # Transcribe audio. transcribe() is a multi-second CPU-bound
            # call: run it on a worker thread so the shared asyncio loop
            # (all audio handling for every connection) keeps flowing.
            result = await asyncio.to_thread(
                self.model.transcribe, file_path, **transcribe_options
            )
            
            decode_time = time.time() - decode_start_time
            logger.bind(tag=TAG).info(f"Whisper transcription completed in {decode_time:.2f}s")
            
            # Extract text from result
            text = result["text"].strip()
            
            if text:
                logger.bind(tag=TAG).info(f"Whisper recognized text: {text}")
                
                # Log additional information if available
                if "language" in result:
                    detected_language = result["language"]
                    logger.bind(tag=TAG).debug(f"Detected language: {detected_language}")
                
                # Log segments for debugging
                if "segments" in result and len(result["segments"]) > 0:
                    num_segments = len(result["segments"])
                    total_duration = sum(seg.get("end", 0) - seg.get("start", 0) for seg in result["segments"])
                    logger.bind(tag=TAG).debug(f"Audio segments: {num_segments}, total duration: {total_duration:.2f}s")
                
                return text, file_path
            else:
                logger.bind(tag=TAG).warning("Whisper returned empty text")
                return "", file_path
                
        except Exception as e:
            logger.bind(tag=TAG).error(f"Whisper speech recognition failed: {e}")
            import traceback
            logger.bind(tag=TAG).debug(f"Exception details: {traceback.format_exc()}")
            return "", file_path
        finally:
            # File cleanup logic
            if self.delete_audio_file and file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.bind(tag=TAG).debug(f"Deleted temporary audio file: {file_path}")
                except Exception as e:
                    logger.bind(tag=TAG).error(f"File deletion failed: {file_path} | Error: {e}")
