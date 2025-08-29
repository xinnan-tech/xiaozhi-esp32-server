import os
import time
import asyncio
import boto3
import json
from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent
from botocore.exceptions import ClientError, NoCredentialsError
from config.logger import setup_logging
from typing import Optional, Tuple, List
from core.providers.asr.base import ASRProviderBase
from core.providers.asr.dto.dto import InterfaceType

TAG = __name__
logger = setup_logging()


class TranscriptEventHandler(TranscriptResultStreamHandler):
    """Handler for Amazon Transcribe streaming events"""
    
    def __init__(self):
        super().__init__()
        self.transcript_text = ""
        self.is_final = False
        self.completed = False
        
    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        results = transcript_event.transcript.results
        for result in results:
            if result.is_partial:
                # Handle partial results for real-time feedback
                for alt in result.alternatives:
                    logger.bind(tag=TAG).debug(f"Partial transcript: {alt.transcript}")
            else:
                # Handle final results
                for alt in result.alternatives:
                    self.transcript_text += alt.transcript + " "
                    logger.bind(tag=TAG).debug(f"Final transcript: {alt.transcript}")
                    self.is_final = True
                    
        # Check if stream is complete
        if not results:
            self.completed = True


class ASRProvider(ASRProviderBase):
    """
    Amazon Transcribe Streaming ASR Provider
    Uses Amazon Transcribe Streaming service for real-time speech-to-text
    """

    def __init__(self, config: dict, delete_audio_file: bool):
        super().__init__(config)
        self.interface_type = InterfaceType.NON_STREAM  # Keep as non-stream for compatibility
        
        # AWS Configuration
        self.aws_access_key_id = config.get("aws_access_key_id")
        self.aws_secret_access_key = config.get("aws_secret_access_key")
        self.aws_region = config.get("aws_region", "us-east-1")
        
        # Transcription Configuration
        self.language_code = config.get("language_code", "en-US")
        self.sample_rate = int(config.get("sample_rate", 16000))
        self.media_encoding = config.get("media_encoding", "pcm")
        
        # File management
        self.output_dir = config.get("output_dir", "./audio_files")
        self.delete_audio_file = delete_audio_file
        
        # Timeout configuration
        timeout = config.get("timeout", 30)
        self.timeout = int(timeout) if timeout else 30
        
        # Initialize AWS session
        try:
            self.session = boto3.Session(
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.aws_region
            )
            
            # Test credentials
            sts_client = self.session.client('sts')
            sts_client.get_caller_identity()
            
        except NoCredentialsError:
            logger.bind(tag=TAG).error("AWS credentials not found. Please configure aws_access_key_id and aws_secret_access_key")
            raise
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to initialize AWS session: {e}")
            raise

        # Ensure output directory exists
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        logger.bind(tag=TAG).info(
            f"Amazon Transcribe Streaming ASR initialized - Region: {self.aws_region}, "
            f"Language: {self.language_code}, Sample Rate: {self.sample_rate}"
        )

    async def speech_to_text(
        self, opus_data: List[bytes], session_id: str, audio_format="opus"
    ) -> Tuple[Optional[str], Optional[str]]:
        """Convert speech data to text using Amazon Transcribe Streaming"""
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

            # Save audio to temporary file for debugging/logging
            audio_file_path = self.save_audio_to_file(pcm_data, session_id)

            # Calculate audio length for logging
            combined_pcm_data = b"".join(pcm_data)
            audio_length_seconds = len(combined_pcm_data) / (self.sample_rate * 2)  # 16-bit audio

            # Perform streaming transcription
            result_text = await self._stream_transcribe(combined_pcm_data)

            elapsed_time = time.time() - start_time
            logger.bind(tag=TAG).info(
                f"Amazon Transcribe Streaming completed in {elapsed_time:.2f}s: {result_text}"
            )

            # Log the transcript for debugging/analysis
            if result_text:
                self.log_audio_transcript(audio_file_path, audio_length_seconds, result_text)

            return result_text, audio_file_path

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
                    logger.bind(tag=TAG).debug(f"Deleted audio file: {audio_file_path}")
                except Exception as e:
                    logger.bind(tag=TAG).warning(f"Failed to delete audio file {audio_file_path}: {e}")

    async def _stream_transcribe(self, pcm_data: bytes) -> Optional[str]:
        """Perform streaming transcription"""
        try:
            # Create streaming client
            client = TranscribeStreamingClient(region=self.aws_region)
            
            # Create event handler
            handler = TranscriptEventHandler()
            
            # Create audio stream generator
            async def audio_generator():
                # Split audio into chunks for streaming
                chunk_size = 1024 * 8  # 8KB chunks
                for i in range(0, len(pcm_data), chunk_size):
                    chunk = pcm_data[i:i + chunk_size]
                    yield {"AudioEvent": {"AudioChunk": chunk}}
                    await asyncio.sleep(0.01)  # Small delay to simulate streaming
            
            # Start streaming transcription
            stream = await client.start_stream_transcription(
                language_code=self.language_code,
                media_sample_rate_hz=self.sample_rate,
                media_encoding=self.media_encoding,
            )
            
            # Set up the event handler
            async def handle_stream():
                async for event in stream.output_stream:
                    await handler.handle_transcript_event(event)
                    if handler.completed:
                        break
            
            # Send audio and handle responses concurrently
            tasks = [
                asyncio.create_task(stream.input_stream.send_audio_event(audio_generator())),
                asyncio.create_task(handle_stream())
            ]
            
            # Wait for completion with timeout
            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True), 
                    timeout=self.timeout
                )
            except asyncio.TimeoutError:
                logger.bind(tag=TAG).warning(f"Streaming transcription timed out after {self.timeout}s")
                return None
            
            # End the stream
            await stream.input_stream.end_stream()
            
            # Return the final transcript
            final_text = handler.transcript_text.strip()
            return final_text if final_text else None
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"Streaming transcription error: {e}")
            return None

    async def _simple_transcribe(self, pcm_data: bytes) -> Optional[str]:
        """Fallback: Simple in-memory transcription without actual streaming"""
        try:
            # This is a simplified approach that processes the entire audio at once
            # but uses the streaming client for better performance than file-based
            
            client = TranscribeStreamingClient(region=self.aws_region)
            
            # Create a simple audio event
            audio_event = {
                "AudioEvent": {
                    "AudioChunk": pcm_data
                }
            }
            
            # For now, let's use a simpler approach
            # In a real implementation, you'd want proper streaming
            # But this gives us the performance benefits without the complexity
            
            # Simulate processing time (much faster than file-based)
            await asyncio.sleep(0.5)  # Much faster than 26 seconds!
            
            # Return a placeholder - in reality you'd implement proper streaming
            # For now, let's fall back to a simple mock for testing
            logger.bind(tag=TAG).info("Using simplified streaming transcription")
            
            # This is where you'd implement the actual streaming logic
            # For now, return None to indicate we need the full implementation
            return None
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"Simple transcription error: {e}")
            return None