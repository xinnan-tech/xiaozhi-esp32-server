import os
import time
import asyncio
import boto3
import json
from botocore.exceptions import ClientError, NoCredentialsError
from config.logger import setup_logging
from typing import Optional, Tuple, List
from core.providers.asr.base import ASRProviderBase
from core.providers.asr.dto.dto import InterfaceType

TAG = __name__
logger = setup_logging()


class ASRProvider(ASRProviderBase):
    """
    Amazon Transcribe ASR Provider
    Uses Amazon Transcribe service for speech-to-text transcription
    """

    def __init__(self, config: dict, delete_audio_file: bool):
        super().__init__(config)
        self.interface_type = InterfaceType.NON_STREAM
        
        # AWS Configuration
        self.aws_access_key_id = config.get("aws_access_key_id")
        self.aws_secret_access_key = config.get("aws_secret_access_key")
        self.aws_region = config.get("aws_region", "us-east-1")
        self.s3_bucket = config.get("s3_bucket")
        
        # Transcription Configuration
        self.language_code = config.get("language_code", "en-US")
        self.sample_rate = config.get("sample_rate", 16000)
        self.media_format = config.get("media_format", "wav")
        self.vocabulary_name = config.get("vocabulary_name")  # Optional custom vocabulary
        self.vocabulary_filter_name = config.get("vocabulary_filter_name")  # Optional vocabulary filter
        
        # File management
        self.output_dir = config.get("output_dir", "./audio_files")
        self.delete_audio_file = delete_audio_file
        self.s3_key_prefix = config.get("s3_key_prefix", "xiaozhi-audio/")
        
        # Timeout configuration
        timeout = config.get("timeout", 60)
        self.timeout = int(timeout) if timeout else 60
        
        # Initialize AWS clients
        try:
            session = boto3.Session(
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.aws_region
            )
            
            self.transcribe_client = session.client('transcribe')
            self.s3_client = session.client('s3')
            
            # Test S3 bucket access
            self._test_s3_access()
            
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
            f"Amazon Transcribe ASR initialized - Region: {self.aws_region}, "
            f"Language: {self.language_code}, S3 Bucket: {self.s3_bucket}"
        )

    def _test_s3_access(self):
        """Test S3 bucket access"""
        try:
            self.s3_client.head_bucket(Bucket=self.s3_bucket)
            logger.bind(tag=TAG).info(f"S3 bucket '{self.s3_bucket}' is accessible")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                logger.bind(tag=TAG).error(f"S3 bucket '{self.s3_bucket}' does not exist")
            elif error_code == '403':
                logger.bind(tag=TAG).error(f"Access denied to S3 bucket '{self.s3_bucket}'")
            else:
                logger.bind(tag=TAG).error(f"Error accessing S3 bucket: {e}")
            raise

    async def speech_to_text(
        self, opus_data: List[bytes], session_id: str, audio_format="opus"
    ) -> Tuple[Optional[str], Optional[str]]:
        """Convert speech data to text using Amazon Transcribe"""
        start_time = time.time()
        audio_file_path = None
        s3_key = None
        job_name = None

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

            # Upload audio file to S3
            s3_key = f"{self.s3_key_prefix}{session_id}_{int(time.time())}.wav"
            
            try:
                self.s3_client.upload_file(audio_file_path, self.s3_bucket, s3_key)
                logger.bind(tag=TAG).debug(f"Uploaded audio to S3: s3://{self.s3_bucket}/{s3_key}")
            except Exception as e:
                logger.bind(tag=TAG).error(f"Failed to upload to S3: {e}")
                return None, audio_file_path

            # Create unique job name
            job_name = f"xiaozhi-transcription-{session_id}-{int(time.time())}"

            # Start transcription job
            media_uri = f"s3://{self.s3_bucket}/{s3_key}"
            
            job_args = {
                'TranscriptionJobName': job_name,
                'Media': {'MediaFileUri': media_uri},
                'MediaFormat': self.media_format,
                'LanguageCode': self.language_code,
                'MediaSampleRateHertz': self.sample_rate
            }

            # Add optional parameters
            if self.vocabulary_name:
                job_args['Settings'] = job_args.get('Settings', {})
                job_args['Settings']['VocabularyName'] = self.vocabulary_name

            if self.vocabulary_filter_name:
                job_args['Settings'] = job_args.get('Settings', {})
                job_args['Settings']['VocabularyFilterName'] = self.vocabulary_filter_name
                job_args['Settings']['VocabularyFilterMethod'] = 'remove'

            # Start the transcription job
            response = self.transcribe_client.start_transcription_job(**job_args)
            logger.bind(tag=TAG).debug(f"Started transcription job: {job_name}")

            # Poll for job completion
            result_text = await self._wait_for_job_completion(job_name)

            elapsed_time = time.time() - start_time
            logger.bind(tag=TAG).info(
                f"Amazon Transcribe completed in {elapsed_time:.2f}s: {result_text}"
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
            
            # Clean up AWS resources
            await self._cleanup_aws_resources(job_name, s3_key)

    async def _wait_for_job_completion(self, job_name: str) -> Optional[str]:
        """Wait for transcription job to complete and return the result"""
        start_time = time.time()
        
        while time.time() - start_time < self.timeout:
            try:
                response = self.transcribe_client.get_transcription_job(
                    TranscriptionJobName=job_name
                )
                
                status = response['TranscriptionJob']['TranscriptionJobStatus']
                
                if status == 'COMPLETED':
                    # Get the transcript
                    transcript_uri = response['TranscriptionJob']['Transcript']['TranscriptFileUri']
                    return await self._fetch_transcript_from_uri(transcript_uri)
                    
                elif status == 'FAILED':
                    failure_reason = response['TranscriptionJob'].get('FailureReason', 'Unknown error')
                    logger.bind(tag=TAG).error(f"Transcription job failed: {failure_reason}")
                    return None
                    
                elif status in ['QUEUED', 'IN_PROGRESS']:
                    # Wait before checking again
                    await asyncio.sleep(1)
                    continue
                    
            except Exception as e:
                logger.bind(tag=TAG).error(f"Error checking job status: {e}")
                return None
                
        logger.bind(tag=TAG).error(f"Transcription job timed out after {self.timeout} seconds")
        return None

    async def _fetch_transcript_from_uri(self, transcript_uri: str) -> Optional[str]:
        """Fetch transcript content from the provided URI"""
        try:
            import urllib.request
            import json
            
            # Use asyncio to run the blocking operation in a thread
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, urllib.request.urlopen, transcript_uri
            )
            
            transcript_data = json.loads(response.read().decode('utf-8'))
            
            # Extract the transcript text
            results = transcript_data.get('results', {})
            transcripts = results.get('transcripts', [])
            
            if transcripts and len(transcripts) > 0:
                return transcripts[0].get('transcript', '')
            else:
                logger.bind(tag=TAG).warning("No transcript found in response")
                return ''
                
        except Exception as e:
            logger.bind(tag=TAG).error(f"Error fetching transcript: {e}")
            return None

    async def _cleanup_aws_resources(self, job_name: str, s3_key: str):
        """Clean up AWS resources"""
        try:
            # Delete transcription job (optional, jobs auto-delete after 90 days)
            if job_name:
                try:
                    self.transcribe_client.delete_transcription_job(
                        TranscriptionJobName=job_name
                    )
                    logger.bind(tag=TAG).debug(f"Deleted transcription job: {job_name}")
                except ClientError as e:
                    # Job might not exist or already deleted
                    if e.response['Error']['Code'] != 'BadRequestException':
                        logger.bind(tag=TAG).warning(f"Could not delete job {job_name}: {e}")

            # Delete S3 object
            if s3_key:
                try:
                    self.s3_client.delete_object(Bucket=self.s3_bucket, Key=s3_key)
                    logger.bind(tag=TAG).debug(f"Deleted S3 object: {s3_key}")
                except ClientError as e:
                    logger.bind(tag=TAG).warning(f"Could not delete S3 object {s3_key}: {e}")

        except Exception as e:
            logger.bind(tag=TAG).error(f"Error during cleanup: {e}")