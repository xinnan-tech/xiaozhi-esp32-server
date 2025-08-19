import os
import time
import httpx
import asyncio
from deepgram import DeepgramClient, PrerecordedOptions, FileSource
from config.logger import setup_logging
from typing import Optional, Tuple, List
from core.providers.asr.base import ASRProviderBase
from core.providers.asr.dto.dto import InterfaceType

TAG = __name__
logger = setup_logging()


class ASRProvider(ASRProviderBase):
    """
    Deepgram ASR Provider
    Uses Deepgram's Nova-2 model for high-accuracy speech-to-text transcription
    """

    def __init__(self, config: dict, delete_audio_file: bool):
        super().__init__(config)
        self.interface_type = InterfaceType.NON_STREAM
        self.api_key = config.get("api_key")
        self.model = config.get("model", "nova-3")
        self.language = config.get("language", "en-IN")  # Default to English
        self.smart_format = config.get("smart_format", True)
        self.punctuate = config.get("punctuate", True)
        self.diarize = config.get("diarize", False)
        self.multichannel = config.get("multichannel", False)
        self.output_dir = config.get("output_dir", "./audio_files")
        self.delete_audio_file = delete_audio_file

        # Timeout configuration
        timeout = config.get("timeout", 60)
        self.timeout = int(timeout) if timeout else 60

        # Initialize Deepgram client
        self.client = DeepgramClient(api_key=self.api_key)

        # Ensure output directory exists
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        logger.bind(tag=TAG).info(
            f"Deepgram ASR initialized with model: {self.model}, "
            f"language: {self.language}, smart_format: {self.smart_format}"
        )

    async def speech_to_text(
        self, opus_data: List[bytes], session_id: str, audio_format="opus"
    ) -> Tuple[Optional[str], Optional[str]]:
        """Convert speech data to text using Deepgram API"""
        start_time = time.time()
        audio_file_path = None

        try:
            # Decode Opus to PCM if needed
            if audio_format == "opus":
                pcm_data = self.decode_opus(opus_data)
                if not pcm_data:
                    logger.bind(tag=TAG).error("Failed to decode Opus audio")
                    return None, None
            else:
                pcm_data = opus_data

            # Save audio to temporary file (Deepgram API requires file upload)
            audio_file_path = self.save_audio_to_file(pcm_data, session_id)

            # Calculate audio length for logging
            audio_length_seconds = len(b"".join(pcm_data)) / (16000 * 2)  # 16kHz, 16-bit

            # Perform transcription
            try:
                # Read the audio file
                with open(audio_file_path, "rb") as audio_file:
                    buffer_data = audio_file.read()

                payload: FileSource = {
                    "buffer": buffer_data,
                }

                # Configure transcription options
                options = PrerecordedOptions(
                    model=self.model,
                    language=self.language,
                    smart_format=self.smart_format,
                    punctuate=self.punctuate,
                    diarize=self.diarize,
                    multichannel=self.multichannel,
                )

                # Use asyncio to run the sync operation in a thread pool
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.client.listen.prerecorded.v("1").transcribe_file(
                        payload, options, timeout=httpx.Timeout(self.timeout)
                    )
                )

                # Extract text from response
                if response.results and response.results.channels:
                    alternatives = response.results.channels[0].alternatives
                    if alternatives and len(alternatives) > 0:
                        result_text = alternatives[0].transcript
                    else:
                        result_text = ""
                else:
                    result_text = ""

                elapsed_time = time.time() - start_time
                logger.bind(tag=TAG).info(
                    f"Deepgram transcription completed in {elapsed_time:.2f}s: {result_text}"
                )

                # Log the transcript for debugging/analysis
                if result_text:
                    self.log_audio_transcript(audio_file_path, audio_length_seconds, result_text)

                return result_text, audio_file_path

            except Exception as e:
                logger.bind(tag=TAG).error(
                    f"Deepgram API error: {str(e)}, type: {type(e).__name__}"
                )
                return None, audio_file_path

        except Exception as e:
            logger.bind(tag=TAG).error(
                f"Speech-to-text error: {str(e)}, type: {type(e).__name__}"
            )
            return None, audio_file_path

        finally:
            # Clean up audio file if configured
            if self.delete_audio_file and audio_file_path and os.path.exists(audio_file_path):
                try:
                    os.remove(audio_file_path)
                    logger.bind(tag=TAG).debug(
                        f"Deleted audio file: {audio_file_path}")
                except Exception as e:
                    logger.bind(tag=TAG).warning(
                        f"Failed to delete audio file {audio_file_path}: {e}"
                    )