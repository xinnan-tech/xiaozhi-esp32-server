import os
import time
import httpx
import asyncio
from groq import Groq
from config.logger import setup_logging
from typing import Optional, Tuple, List
from core.providers.asr.base import ASRProviderBase
from core.providers.asr.dto.dto import InterfaceType

TAG = __name__
logger = setup_logging()


class ASRProvider(ASRProviderBase):
    """
    Groq Whisper ASR Provider
    Uses Groq's API for Whisper-based speech-to-text transcription
    """

    def __init__(self, config: dict, delete_audio_file: bool):
        super().__init__()
        self.interface_type = InterfaceType.NON_STREAM
        self.api_key = config.get("api_key")
        self.model = config.get("model", "whisper-large-v3")
        self.language = config.get("language", "zh")  # Default to Chinese
        self.temperature = config.get("temperature", 0.0)
        self.response_format = config.get("response_format", "text")
        self.output_dir = config.get("output_dir", "./audio_files")
        self.delete_audio_file = delete_audio_file

        # Groq base URL (can be overridden in config)
        self.base_url = config.get("base_url", "https://api.groq.com")

        # Timeout configuration
        timeout = config.get("timeout", 60)
        self.timeout = int(timeout) if timeout else 60

        # Initialize Groq client
        self.client = Groq(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
            max_retries=2
        )

        # Ensure output directory exists
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        logger.bind(tag=TAG).info(
            f"Groq Whisper ASR initialized with model: {self.model}, "
            f"language: {self.language}, temperature: {self.temperature}"
        )

    async def speech_to_text(
        self, opus_data: List[bytes], session_id: str, audio_format="opus"
    ) -> Tuple[Optional[str], Optional[str]]:
        """Convert speech data to text using Groq Whisper API"""
        start_time = time.time()

        try:
            # Decode Opus to PCM if needed
            if audio_format == "opus":
                pcm_data = self.decode_opus(opus_data)
                if not pcm_data:
                    logger.bind(tag=TAG).error("Failed to decode Opus audio")
                    return None, None
            else:
                pcm_data = opus_data

            # Save audio to temporary file (Groq API requires file upload)
            audio_file_path = self.save_audio_to_file(pcm_data, session_id)

            # Perform transcription
            try:
                with open(audio_file_path, "rb") as audio_file:
                    # Use asyncio to run the sync operation in a thread pool
                    loop = asyncio.get_event_loop()
                    transcription = await loop.run_in_executor(
                        None,
                        lambda: self.client.audio.transcriptions.create(
                            model=self.model,
                            file=audio_file,
                            language=self.language,
                            temperature=self.temperature,
                            response_format=self.response_format
                        )
                    )

                # Extract text based on response format
                if self.response_format == "text":
                    result_text = transcription
                elif hasattr(transcription, 'text'):
                    result_text = transcription.text
                else:
                    result_text = str(transcription)

                elapsed_time = time.time() - start_time
                logger.bind(tag=TAG).info(
                    f"Groq Whisper transcription completed in {elapsed_time:.2f}s: {result_text}"
                )

                return result_text, audio_file_path

            except Exception as e:
                logger.bind(tag=TAG).error(
                    f"Groq API error: {str(e)}, type: {type(e).__name__}"
                )
                return None, audio_file_path

            finally:
                # Clean up audio file if configured
                if self.delete_audio_file and os.path.exists(audio_file_path):
                    try:
                        os.remove(audio_file_path)
                        logger.bind(tag=TAG).debug(
                            f"Deleted audio file: {audio_file_path}")
                    except Exception as e:
                        logger.bind(tag=TAG).warning(
                            f"Failed to delete audio file {audio_file_path}: {e}"
                        )

        except Exception as e:
            logger.bind(tag=TAG).error(
                f"Speech-to-text error: {str(e)}, type: {type(e).__name__}"
            )
            return None, None
