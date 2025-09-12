import os
import time
import json
import asyncio
from google.cloud import speech_v2
from google.api_core import exceptions
from google.api_core.client_options import ClientOptions
from config.logger import setup_logging
from typing import Optional, Tuple, List, AsyncIterator
from core.providers.asr.base import ASRProviderBase
from core.providers.asr.dto.dto import InterfaceType

TAG = __name__
logger = setup_logging()


class ASRProvider(ASRProviderBase):
    """
    Google Cloud Speech-to-Text v2 Provider with Chirp 2 model support
    Chirp 2 is Google's next-generation universal speech model with improved accuracy
    """

    def __init__(self, config: dict, delete_audio_file: bool):
        super().__init__(config)
        self.interface_type = InterfaceType.NON_STREAM
        
        # Google Cloud configuration
        self.project_id = config.get("project_id")
        self.location = config.get("location", "global")  # Chirp 2 is available globally
        self.credentials_path = config.get("credentials_path")
        
        # Model configuration - Chirp 2 specific
        self.model = config.get("model", "chirp_2")  # Use Chirp 2 by default
        language_codes_from_config = config.get("language_codes", ["en-US"])
        
        # Ensure language_codes is never empty (Google API requirement)
        if not language_codes_from_config or not isinstance(language_codes_from_config, list):
            self.language_codes = ["en-US"]
            logger.bind(tag=TAG).warning(f"Invalid or empty language_codes in config, using default: ['en-US']")
        else:
            self.language_codes = language_codes_from_config
        
        # Debug logging for language codes
        logger.bind(tag=TAG).info(f"Configured language_codes: {self.language_codes} (type: {type(self.language_codes)})")
        
        # Audio configuration
        self.sample_rate_hertz = config.get("sample_rate_hertz", 16000)
        self.encoding = config.get("encoding", "LINEAR16")
        
        # Recognition configuration
        self.enable_automatic_punctuation = config.get("enable_automatic_punctuation", True)
        self.enable_word_time_offsets = config.get("enable_word_time_offsets", False)
        self.enable_word_confidence = config.get("enable_word_confidence", False)
        self.enable_spoken_punctuation = config.get("enable_spoken_punctuation", False)
        self.enable_spoken_emojis = config.get("enable_spoken_emojis", False)
        
        # File management
        self.output_dir = config.get("output_dir", "./audio_files")
        self.delete_audio_file = delete_audio_file
        
        # Set credentials if provided
        if self.credentials_path:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.credentials_path
        
        # Initialize the Speech client with v2 API
        try:
            # For Chirp 2, use regional endpoint and recognizer
            if self.model == "chirp_2":
                # Use regional API endpoint for Chirp 2
                api_endpoint = f"{self.location}-speech.googleapis.com"
                client_options = ClientOptions(api_endpoint=api_endpoint)
                self.client = speech_v2.SpeechClient(client_options=client_options)
                
                # Use regional recognizer path to match regional endpoint
                # Note: When using regional endpoint, recognizer path must also use same region
                self.recognizer_name = f"projects/{self.project_id}/locations/{self.location}/recognizers/_"
                logger.bind(tag=TAG).info(f"Using regional API endpoint: {api_endpoint}")
            else:
                # Use default global client and recognizer for standard models
                self.client = speech_v2.SpeechClient()
                self.recognizer_name = f"projects/{self.project_id}/locations/global/recognizers/_"
            
            logger.bind(tag=TAG).info(
                f"Google Speech v2 initialized with model: {self.model}, "
                f"project: {self.project_id}, recognizer: {self.recognizer_name}"
            )
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to initialize Google Speech v2 client: {e}")
            raise
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Streaming session management
        self.streaming_sessions = {}  # conn.session_id -> streaming session data

    def _get_audio_encoding(self):
        """Map encoding string to Google Speech enum"""
        try:
            encoding_map = {
                "LINEAR16": speech_v2.ExplicitDecodingConfig.AudioEncoding.LINEAR16,
                "FLAC": speech_v2.ExplicitDecodingConfig.AudioEncoding.FLAC,
                "MULAW": speech_v2.ExplicitDecodingConfig.AudioEncoding.MULAW,
                "AMR": speech_v2.ExplicitDecodingConfig.AudioEncoding.AMR,
                "AMR_WB": speech_v2.ExplicitDecodingConfig.AudioEncoding.AMR_WB,
                "OGG_OPUS": speech_v2.ExplicitDecodingConfig.AudioEncoding.OGG_OPUS,
                "MP3": speech_v2.ExplicitDecodingConfig.AudioEncoding.MP3,
                "WEBM_OPUS": speech_v2.ExplicitDecodingConfig.AudioEncoding.WEBM_OPUS,
            }
            
            # Add SPEEX if available (not all versions support it)
            if hasattr(speech_v2.ExplicitDecodingConfig.AudioEncoding, 'SPEEX_WITH_HEADER_BYTE'):
                encoding_map["SPEEX_WITH_HEADER_BYTE"] = speech_v2.ExplicitDecodingConfig.AudioEncoding.SPEEX_WITH_HEADER_BYTE
            
            return encoding_map.get(self.encoding, speech_v2.ExplicitDecodingConfig.AudioEncoding.LINEAR16)
        except AttributeError as e:
            logger.bind(tag=TAG).warning(f"Audio encoding {self.encoding} not supported, using LINEAR16: {e}")
            return speech_v2.ExplicitDecodingConfig.AudioEncoding.LINEAR16

    async def speech_to_text(
        self, opus_data: List[bytes], session_id: str, audio_format="opus"
    ) -> Tuple[Optional[str], Optional[str]]:
        """Convert speech data to text using Google Cloud Speech v2 API with Chirp 2"""
        start_time = time.time()
        audio_file_path = None
        
        try:
            # Decode Opus to PCM if needed
            if audio_format == "opus":
                pcm_data = self.decode_opus(opus_data)
                if not pcm_data:
                    logger.bind(tag=TAG).error("Failed to decode Opus audio")
                    return "", None
            else:
                pcm_data = opus_data
            
            # Save audio to file for logging/debugging
            audio_file_path = self.save_audio_to_file(pcm_data, session_id)
            
            # Combine PCM data
            audio_content = b"".join(pcm_data)
            
            # Calculate audio length for logging
            audio_length_seconds = len(audio_content) / (self.sample_rate_hertz * 2)  # 16-bit audio
            
            # Configure recognition request - use model name as-is
            model_name = self.model
            encoding = self._get_audio_encoding()
            logger.bind(tag=TAG).debug(f"Using model: {model_name} for recognition")
            logger.bind(tag=TAG).debug(f"Audio encoding: {encoding}, sample_rate: {self.sample_rate_hertz}, audio_length: {len(audio_content)} bytes")
            
            # Configure recognition request based on model type
            if self.model == "chirp_2":
                # Use explicit decoding config for Chirp 2 with proper audio format
                config = speech_v2.RecognitionConfig(
                    explicit_decoding_config=speech_v2.ExplicitDecodingConfig(
                        encoding=encoding,
                        sample_rate_hertz=self.sample_rate_hertz,
                        audio_channel_count=1,
                    ),
                    language_codes=self.language_codes,
                    model=model_name,  # chirp_2
                    features=speech_v2.RecognitionFeatures(
                        enable_automatic_punctuation=self.enable_automatic_punctuation,
                        enable_word_time_offsets=self.enable_word_time_offsets,
                        enable_word_confidence=self.enable_word_confidence,
                        enable_spoken_punctuation=self.enable_spoken_punctuation,
                        enable_spoken_emojis=self.enable_spoken_emojis,
                        profanity_filter=False,
                    ),
                )
            else:
                # Use explicit decoding for standard models
                config = speech_v2.RecognitionConfig(
                    explicit_decoding_config=speech_v2.ExplicitDecodingConfig(
                        encoding=encoding,
                        sample_rate_hertz=self.sample_rate_hertz,
                        audio_channel_count=1,
                    ),
                    language_codes=self.language_codes,
                    model=model_name,
                    features=speech_v2.RecognitionFeatures(
                        enable_automatic_punctuation=self.enable_automatic_punctuation,
                        enable_word_time_offsets=self.enable_word_time_offsets,
                        enable_word_confidence=self.enable_word_confidence,
                        enable_spoken_punctuation=self.enable_spoken_punctuation,
                        enable_spoken_emojis=self.enable_spoken_emojis,
                        profanity_filter=False,
                    ),
                )
            
            # Create recognition request
            request = speech_v2.RecognizeRequest(
                recognizer=self.recognizer_name,
                config=config,
                content=audio_content,
            )
            
            # Perform synchronous speech recognition
            try:
                response = self.client.recognize(request=request)
                
                # Extract transcription from response
                transcript = ""
                confidence_scores = []
                
                for result in response.results:
                    # Get the best alternative (highest confidence)
                    if result.alternatives:
                        best_alternative = result.alternatives[0]
                        transcript += best_alternative.transcript + " "
                        
                        # Collect confidence scores if available
                        if hasattr(best_alternative, 'confidence'):
                            confidence_scores.append(best_alternative.confidence)
                        
                        # Log word-level details if enabled
                        if self.enable_word_time_offsets and hasattr(best_alternative, 'words'):
                            for word_info in best_alternative.words:
                                logger.bind(tag=TAG).debug(
                                    f"Word: {word_info.word}, "
                                    f"Start: {word_info.start_offset}, "
                                    f"End: {word_info.end_offset}"
                                )
                
                transcript = transcript.strip()
                
                # Calculate average confidence if available
                avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else None
                
                elapsed_time = time.time() - start_time
                logger.bind(tag=TAG).info(
                    f"Google Speech v2 (Chirp 2) transcription completed in {elapsed_time:.2f}s"
                    f"{f', confidence: {avg_confidence:.2f}' if avg_confidence else ''}: {transcript}"
                )
                
                # Log the transcript for debugging/analysis
                if transcript:
                    self.log_audio_transcript(audio_file_path, audio_length_seconds, transcript)
                
                return transcript, audio_file_path
                
            except exceptions.GoogleAPIError as e:
                logger.bind(tag=TAG).error(f"Google Speech API error: {e}")
                return "", audio_file_path
            
        except Exception as e:
            logger.bind(tag=TAG).error(
                f"Speech-to-text error: {str(e)}, type: {type(e).__name__}"
            )
            import traceback
            logger.bind(tag=TAG).debug(f"Traceback: {traceback.format_exc()}")
            return "", audio_file_path
        
        finally:
            # Clean up audio file if configured
            if self.delete_audio_file and audio_file_path and os.path.exists(audio_file_path):
                try:
                    os.remove(audio_file_path)
                    logger.bind(tag=TAG).debug(f"Deleted audio file: {audio_file_path}")
                except Exception as e:
                    logger.bind(tag=TAG).warning(
                        f"Failed to delete audio file {audio_file_path}: {e}"
                    )

    async def start_streaming_session(self, conn, session_id: str) -> bool:
        """Start a streaming ASR session for real-time transcription.
        
        Args:
            conn: Connection object
            session_id: Unique session identifier
            
        Returns:
            True if session started successfully, False otherwise
        """
        try:
            logger.bind(tag=TAG).info(f"[STREAM-START] Starting streaming session: {session_id}")
            
            # Validate language codes
            safe_language_codes = self.language_codes if self.language_codes else ["en-US"]
            logger.bind(tag=TAG).debug(f"[STREAM-START] Using language_codes: {safe_language_codes}")
            
            # Create simplified session data with direct audio buffer
            session_data = {
                'language_codes': safe_language_codes,
                'model': self.model,
                'audio_buffer': [],  # Simple list to collect audio chunks
                'stream_iterator': None,
                'streaming_task': None,
                'final_transcript': "",
                'partial_transcript': "",
                'session_active': True,
                'audio_count': 0
            }
            
            # Store session
            self.streaming_sessions[session_id] = session_data
            logger.bind(tag=TAG).info(f"[STREAM-START] Session {session_id} created with simplified data structure")
            
            # Start the streaming task
            session_data['streaming_task'] = asyncio.create_task(
                self._simplified_streaming_task(session_id, session_data)
            )
            
            logger.bind(tag=TAG).info(f"[STREAM-START] Streaming session {session_id} started successfully")
            return True
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"[STREAM-START] Failed to start streaming session {session_id}: {e}")
            import traceback
            logger.bind(tag=TAG).error(f"[STREAM-START] Traceback: {traceback.format_exc()}")
            return False

    async def _simplified_streaming_task(self, session_id: str, session_data: dict):
        """Simplified streaming task that processes audio directly without complex queues."""
        logger.bind(tag=TAG).info(f"[STREAM-TASK] Starting simplified streaming task for session {session_id}")
        
        try:
            # Create streaming configuration with explicit decoding (matches non-streaming config)
            config = speech_v2.StreamingRecognitionConfig(
                config=speech_v2.RecognitionConfig(
                    explicit_decoding_config=speech_v2.ExplicitDecodingConfig(
                        encoding=self._get_audio_encoding(),
                        sample_rate_hertz=self.sample_rate_hertz,
                        audio_channel_count=1,
                    ),
                    language_codes=session_data['language_codes'],
                    model=session_data['model'],
                    features=speech_v2.RecognitionFeatures(
                        enable_automatic_punctuation=self.enable_automatic_punctuation,
                        enable_word_time_offsets=self.enable_word_time_offsets,
                        enable_word_confidence=self.enable_word_confidence,
                        enable_spoken_punctuation=self.enable_spoken_punctuation,
                        enable_spoken_emojis=self.enable_spoken_emojis,
                        profanity_filter=False,
                    ),
                ),
                streaming_features=speech_v2.StreamingRecognitionFeatures(
                    interim_results=True,
                    enable_voice_activity_events=True,
                )
            )
            
            logger.bind(tag=TAG).info(f"[STREAM-TASK] Created config for {session_id}:")
            logger.bind(tag=TAG).info(f"  - Language codes: {session_data['language_codes']}")
            logger.bind(tag=TAG).info(f"  - Model: {session_data['model']}")
            logger.bind(tag=TAG).info(f"  - Encoding: {self._get_audio_encoding()}")
            logger.bind(tag=TAG).info(f"  - Sample rate: {self.sample_rate_hertz} Hz")
            logger.bind(tag=TAG).info(f"  - Channels: 1 (mono)")
            
            # Use a thread-safe queue to pass audio data to generator
            import queue
            import threading
            
            audio_queue = queue.Queue()
            
            def audio_generator():
                """Generator that yields audio requests to Google API."""
                logger.bind(tag=TAG).debug(f"[AUDIO-GEN] Starting audio generator for {session_id}")
                
                # First request: configuration
                config_request = speech_v2.StreamingRecognizeRequest(
                    recognizer=self.recognizer_name,
                    streaming_config=config
                )
                logger.bind(tag=TAG).info(f"[AUDIO-GEN] Sending config request for {session_id}")
                yield config_request
                
                # Track audio chunks sent
                chunks_sent = 0
                
                # Process audio chunks from queue
                while True:
                    try:
                        # Wait for audio data with timeout
                        audio_chunk = audio_queue.get(timeout=1.0)
                        
                        if audio_chunk is None:  # End signal
                            logger.bind(tag=TAG).info(f"[AUDIO-GEN] Received end signal for {session_id}")
                            break
                        
                        chunks_sent += 1
                        logger.bind(tag=TAG).info(f"[AUDIO-GEN] Sending audio chunk #{chunks_sent} ({len(audio_chunk)} bytes) for {session_id}")
                        
                        # Create and yield audio request
                        audio_request = speech_v2.StreamingRecognizeRequest(audio=audio_chunk)
                        yield audio_request
                        
                    except queue.Empty:
                        # Timeout - check if session is still active
                        if not session_data['session_active']:
                            logger.bind(tag=TAG).info(f"[AUDIO-GEN] Session {session_id} no longer active, stopping generator")
                            break
                        continue
                    except Exception as e:
                        logger.bind(tag=TAG).error(f"[AUDIO-GEN] Error in generator for {session_id}: {e}")
                        break
                
                logger.bind(tag=TAG).info(f"[AUDIO-GEN] Audio generator finished for {session_id} (sent {chunks_sent} chunks)")
            
            # Function to feed audio data from buffer to queue
            def audio_feeder():
                """Feed audio data from session buffer to generator queue."""
                logger.bind(tag=TAG).debug(f"[AUDIO-FEEDER] Starting audio feeder for {session_id}")
                
                try:
                    while session_data['session_active']:
                        # Check if we have audio data in buffer
                        if session_data['audio_buffer']:
                            audio_chunk = session_data['audio_buffer'].pop(0)
                            audio_queue.put(audio_chunk)
                            logger.bind(tag=TAG).debug(f"[AUDIO-FEEDER] Moved audio chunk to queue for {session_id}")
                        else:
                            # No audio data, sleep briefly
                            import time
                            time.sleep(0.01)  # 10ms
                    
                    # Send end signal when session ends
                    audio_queue.put(None)
                    logger.bind(tag=TAG).debug(f"[AUDIO-FEEDER] Sent end signal for {session_id}")
                    
                except Exception as e:
                    logger.bind(tag=TAG).error(f"[AUDIO-FEEDER] Error in feeder for {session_id}: {e}")
                finally:
                    logger.bind(tag=TAG).debug(f"[AUDIO-FEEDER] Audio feeder finished for {session_id}")
            
            # Start audio feeder in separate thread
            feeder_thread = threading.Thread(target=audio_feeder, daemon=True)
            feeder_thread.start()
            
            # Start streaming recognition
            logger.bind(tag=TAG).info(f"[STREAM-TASK] Starting Google API streaming for {session_id}")
            responses = self.client.streaming_recognize(audio_generator())
            
            # Process responses
            response_count = 0
            for response in responses:
                if not session_data['session_active']:
                    logger.bind(tag=TAG).info(f"[STREAM-TASK] Session {session_id} no longer active, stopping")
                    break
                
                response_count += 1
                logger.bind(tag=TAG).debug(f"[STREAM-TASK] Processing response #{response_count} for {session_id}")
                
                # Process recognition results
                for result in response.results:
                    if result.alternatives:
                        transcript = result.alternatives[0].transcript
                        confidence = getattr(result.alternatives[0], 'confidence', 0.0)
                        
                        if result.is_final:
                            session_data['final_transcript'] += transcript + " "
                            session_data['partial_transcript'] = ""
                            logger.bind(tag=TAG).info(f"[STREAM-TASK] FINAL transcript for {session_id}: '{transcript}' (confidence: {confidence:.2f})")
                        else:
                            session_data['partial_transcript'] = transcript
                            logger.bind(tag=TAG).debug(f"[STREAM-TASK] PARTIAL transcript for {session_id}: '{transcript}'")
            
            logger.bind(tag=TAG).info(f"[STREAM-TASK] Completed streaming for {session_id} (processed {response_count} responses)")
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"[STREAM-TASK] Error in streaming task for {session_id}: {e}")
            import traceback
            logger.bind(tag=TAG).error(f"[STREAM-TASK] Traceback: {traceback.format_exc()}")
        finally:
            logger.bind(tag=TAG).info(f"[STREAM-TASK] Streaming task ended for {session_id}")

    async def stream_audio_chunk(self, conn, audio_chunk: bytes, session_id: str) -> Optional[str]:
        """Stream an audio chunk to the active ASR session.
        
        Args:
            conn: Connection object
            audio_chunk: PCM audio data to stream
            session_id: Session identifier
            
        Returns:
            Latest partial transcript if available, None otherwise
        """
        logger.bind(tag=TAG).info(f"[STREAM-AUDIO] stream_audio_chunk called for {session_id} with {len(audio_chunk)} bytes")
        try:
            if session_id not in self.streaming_sessions:
                logger.bind(tag=TAG).warning(f"[STREAM-AUDIO] No active streaming session for {session_id}")
                return None
                
            session_data = self.streaming_sessions[session_id]
            session_data['audio_count'] += 1
            
            # Add audio chunk directly to buffer
            session_data['audio_buffer'].append(audio_chunk)
            logger.bind(tag=TAG).info(f"[STREAM-AUDIO] Added audio chunk #{session_data['audio_count']} ({len(audio_chunk)} bytes) to session {session_id}. Buffer size: {len(session_data['audio_buffer'])}")
            
            # Return latest partial transcript if available
            partial = session_data.get('partial_transcript', '')
            if partial:
                logger.bind(tag=TAG).debug(f"[STREAM-AUDIO] Returning partial transcript for {session_id}: '{partial}'")
                return partial
                
            return None
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"[STREAM-AUDIO] Error streaming audio chunk for {session_id}: {e}")
            return None

    async def end_streaming_session(self, conn, session_id: str) -> Tuple[str, Optional[str]]:
        """End the streaming ASR session and get final transcript.
        
        Args:
            conn: Connection object
            session_id: Session identifier
            
        Returns:
            Tuple of (final_transcript, file_path)
        """
        try:
            if session_id not in self.streaming_sessions:
                logger.bind(tag=TAG).warning(f"[STREAM-END] No active streaming session for {session_id}")
                return "", None
                
            session_data = self.streaming_sessions[session_id]
            logger.bind(tag=TAG).info(f"[STREAM-END] Ending streaming session: {session_id}")
            
            # Signal end of audio stream
            session_data['session_active'] = False
            logger.bind(tag=TAG).debug(f"[STREAM-END] Marked session {session_id} as inactive")
            
            # Wait for streaming task to complete
            if session_data['streaming_task']:
                try:
                    logger.bind(tag=TAG).debug(f"[STREAM-END] Waiting for streaming task to complete for {session_id}")
                    await asyncio.wait_for(session_data['streaming_task'], timeout=3.0)
                    logger.bind(tag=TAG).debug(f"[STREAM-END] Streaming task completed for {session_id}")
                except asyncio.TimeoutError:
                    logger.bind(tag=TAG).warning(f"[STREAM-END] Streaming task timeout for {session_id}, cancelling")
                    session_data['streaming_task'].cancel()
                    try:
                        await session_data['streaming_task']
                    except asyncio.CancelledError:
                        pass
            
            # Get final transcript
            final_transcript = session_data.get('final_transcript', '').strip()
            audio_count = session_data.get('audio_count', 0)
            
            logger.bind(tag=TAG).info(f"[STREAM-END] Session {session_id} processed {audio_count} audio chunks")
            logger.bind(tag=TAG).info(f"[STREAM-END] Final transcript for {session_id}: '{final_transcript}'")
            
            # Clean up session
            del self.streaming_sessions[session_id]
            
            return final_transcript, None
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"[STREAM-END] Error ending streaming session {session_id}: {e}")
            import traceback
            logger.bind(tag=TAG).error(f"[STREAM-END] Traceback: {traceback.format_exc()}")
            return "", None