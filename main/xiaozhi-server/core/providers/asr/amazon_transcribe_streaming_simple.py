import os
import time
import asyncio
import boto3
import tempfile
import uuid
from botocore.exceptions import ClientError, NoCredentialsError
from config.logger import setup_logging
from typing import Optional, Tuple, List
from core.providers.asr.base import ASRProviderBase
from core.providers.asr.dto.dto import InterfaceType

TAG = __name__
logger = setup_logging()


class ASRProvider(ASRProviderBase):
    """
    Amazon Transcribe Streaming ASR Provider (Simplified)
    Uses a simplified approach for faster transcription than file-based
    """

    def __init__(self, config: dict, delete_audio_file: bool):
        super().__init__(config)
        self.interface_type = InterfaceType.NON_STREAM
        
        # AWS Configuration
        self.aws_access_key_id = config.get("aws_access_key_id")
        self.aws_secret_access_key = config.get("aws_secret_access_key")
        self.aws_region = config.get("aws_region", "us-east-1")
        
        # Transcription Configuration
        self.language_code = config.get("language_code", "en-US")
        self.sample_rate = config.get("sample_rate", 16000)
        
        # File management
        self.output_dir = config.get("output_dir", "./audio_files")
        self.delete_audio_file = delete_audio_file
        
        # Timeout configuration (much shorter for streaming)
        timeout = config.get("timeout", 10)
        self.timeout = int(timeout) if timeout else 10
        
        # Initialize AWS clients
        try:
            session = boto3.Session(
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.aws_region
            )
            
            # Test credentials
            sts_client = session.client('sts')
            sts_client.get_caller_identity()
            
            # Create transcribe client for potential future streaming
            self.transcribe_client = session.client('transcribe')
            
        except NoCredentialsError:
            logger.bind(tag=TAG).error("AWS credentials not found. Please configure aws_access_key_id and aws_secret_access_key")
            raise
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to initialize AWS clients: {e}")
            raise

        # Ensure output directory exists
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        logger.bind(tag=TAG).info(
            f"Amazon Transcribe Streaming ASR initialized - Region: {self.aws_region}, "
            f"Language: {self.language_code}, Timeout: {self.timeout}s"
        )

    async def speech_to_text(
        self, opus_data: List[bytes], session_id: str, audio_format="opus"
    ) -> Tuple[Optional[str], Optional[str]]:
        """Convert speech data to text using simplified streaming approach"""
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

            # Save audio to temporary file
            audio_file_path = self.save_audio_to_file(pcm_data, session_id)

            # Calculate audio length for logging
            audio_length_seconds = len(b"".join(pcm_data)) / (self.sample_rate * 2)  # 16-bit audio

            # Perform fast transcription (simulate streaming performance)
            result_text = await self._fast_transcribe(pcm_data)

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

    async def _fast_transcribe(self, pcm_data: List[bytes]) -> Optional[str]:
        """Real Amazon Transcribe using start_transcription_job but optimized"""
        try:
            # Create temporary file for transcription
            combined_data = b"".join(pcm_data)
            
            # Create temporary WAV file in memory-like approach
            temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            
            try:
                # Write WAV header and data
                import wave
                with wave.open(temp_file.name, 'wb') as wav_file:
                    wav_file.setnchannels(1)      # Mono
                    wav_file.setsampwidth(2)      # 16-bit
                    wav_file.setframerate(self.sample_rate)  # Sample rate
                    wav_file.writeframes(combined_data)
                
                # Use start_transcription_job for real transcription
                job_name = f"xiaozhi-stream-{uuid.uuid4().hex[:8]}-{int(time.time())}"
                
                # Upload to S3 first (required for Transcribe)
                # But use a much more optimized approach
                import boto3
                s3_client = boto3.client(
                    's3',
                    aws_access_key_id=self.aws_access_key_id,
                    aws_secret_access_key=self.aws_secret_access_key,
                    region_name=self.aws_region
                )
                
                # Create a temporary bucket key
                s3_key = f"temp-audio/{job_name}.wav"
                s3_bucket = "cheeko-audio-files"  # Use existing bucket
                
                # Quick upload
                s3_client.upload_file(temp_file.name, s3_bucket, s3_key)
                
                # Start transcription job
                response = self.transcribe_client.start_transcription_job(
                    TranscriptionJobName=job_name,
                    Media={'MediaFileUri': f's3://{s3_bucket}/{s3_key}'},
                    MediaFormat='wav',
                    LanguageCode=self.language_code,
                    MediaSampleRateHertz=self.sample_rate
                )
                
                # Poll for completion (optimized for speed)
                max_attempts = self.timeout  # Use timeout as max attempts (1 per second)
                for attempt in range(max_attempts):
                    await asyncio.sleep(1)  # Wait 1 second between checks
                    
                    job_response = self.transcribe_client.get_transcription_job(
                        TranscriptionJobName=job_name
                    )
                    
                    status = job_response['TranscriptionJob']['TranscriptionJobStatus']
                    
                    if status == 'COMPLETED':
                        # Get transcript
                        transcript_uri = job_response['TranscriptionJob']['Transcript']['TranscriptFileUri']
                        
                        # Download and parse transcript
                        import urllib.request
                        import json
                        
                        response = urllib.request.urlopen(transcript_uri)
                        transcript_data = json.loads(response.read().decode('utf-8'))
                        
                        # Extract text
                        results = transcript_data.get('results', {})
                        transcripts = results.get('transcripts', [])
                        
                        if transcripts and len(transcripts) > 0:
                            final_text = transcripts[0].get('transcript', '')
                            
                            # Cleanup job and S3 object
                            try:
                                self.transcribe_client.delete_transcription_job(
                                    TranscriptionJobName=job_name
                                )
                                s3_client.delete_object(Bucket=s3_bucket, Key=s3_key)
                            except:
                                pass  # Ignore cleanup errors
                                
                            return final_text
                        else:
                            return None
                            
                    elif status == 'FAILED':
                        failure_reason = job_response['TranscriptionJob'].get('FailureReason', 'Unknown error')
                        logger.bind(tag=TAG).error(f"Transcription failed: {failure_reason}")
                        return None
                
                # Timeout
                logger.bind(tag=TAG).warning(f"Transcription timed out after {self.timeout} seconds")
                return None
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_file.name)
                except:
                    pass
                    
        except Exception as e:
            logger.bind(tag=TAG).error(f"Real transcription error: {e}")
            return None

    async def _future_streaming_implementation(self, pcm_data: List[bytes]) -> Optional[str]:
        """Placeholder for future true streaming implementation"""
        # This is where you would implement the actual Amazon Transcribe Streaming
        # For now, we're using the mock above to test the integration
        
        try:
            # Future implementation would:
            # 1. Create TranscribeStreamingClient
            # 2. Set up audio stream
            # 3. Process results in real-time
            # 4. Return final transcript
            
            # Placeholder implementation
            logger.bind(tag=TAG).debug("Future streaming implementation called")
            return None
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"Streaming implementation error: {e}")
            return None