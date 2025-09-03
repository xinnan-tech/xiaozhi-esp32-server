import time
import asyncio
import threading
from typing import Optional, Tuple, List, Callable
from collections import deque
from config.logger import setup_logging
from core.providers.asr.dto.dto import InterfaceType
from core.providers.asr.base import ASRProviderBase
import requests
import io
import wave

TAG = __name__
logger = setup_logging()


class ASRProvider(ASRProviderBase):
    """
    Streaming OpenAI ASR Provider with chunked audio processing
    Processes audio in chunks for near real-time transcription
    """
    
    def __init__(self, config: dict, delete_audio_file: bool):
        super().__init__(config)
        self.interface_type = InterfaceType.STREAM
        self.api_key = config.get("api_key")
        self.api_url = config.get("api_url", "https://api.openai.com/v1/audio/transcriptions")
        self.model = config.get("model_name", "whisper-1")
        self.language = config.get("language", "en")
        self.output_dir = config.get("output_dir", "tmp/")
        self.delete_audio_file = delete_audio_file
        
        # Streaming configuration
        self.chunk_duration = config.get("chunk_duration", 3.0)  # seconds
        self.overlap_duration = config.get("overlap_duration", 0.5)  # seconds for word boundary
        self.sample_rate = config.get("sample_rate", 16000)
        self.channels = config.get("channels", 1)
        
        # Audio buffering
        self.audio_buffer = deque()
        self.chunk_size = int(self.chunk_duration * self.sample_rate * 2 * self.channels)  # 16-bit samples
        self.overlap_size = int(self.overlap_duration * self.sample_rate * 2 * self.channels)
        
        # Threading for async processing
        self.processing_queue = asyncio.Queue()
        self.result_callbacks = []
        self.is_streaming = False
        self.session_id = None
        
        logger.bind(tag=TAG).info(f"Streaming ASR initialized - chunk: {self.chunk_duration}s, overlap: {self.overlap_duration}s")

    async def start_streaming(self, session_id: str, callback: Callable[[str, bool], None]) -> bool:
        """
        Start streaming transcription session
        
        Args:
            session_id: Unique session identifier
            callback: Function to call with partial results (text, is_final)
        
        Returns:
            bool: True if streaming started successfully
        """
        try:
            self.session_id = session_id
            self.is_streaming = True
            self.result_callbacks.append(callback)
            
            # Start processing task
            asyncio.create_task(self._process_chunks())
            
            logger.bind(tag=TAG).info(f"Started streaming ASR for session: {session_id}")
            return True
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to start streaming: {str(e)}")
            return False

    async def add_audio_chunk(self, audio_data: bytes) -> None:
        """
        Add audio data to processing buffer
        
        Args:
            audio_data: Raw PCM audio bytes (16-bit, mono/stereo)
        """
        if not self.is_streaming:
            return
            
        self.audio_buffer.extend(audio_data)
        
        # Check if we have enough data for a chunk
        if len(self.audio_buffer) >= self.chunk_size:
            await self._extract_and_queue_chunk()

    async def _extract_and_queue_chunk(self) -> None:
        """Extract a chunk from buffer and queue for processing"""
        if len(self.audio_buffer) < self.chunk_size:
            return
            
        # Extract chunk with overlap for previous chunk
        chunk_data = bytes(list(self.audio_buffer)[:self.chunk_size])
        
        # Remove processed data but keep overlap
        for _ in range(self.chunk_size - self.overlap_size):
            if self.audio_buffer:
                self.audio_buffer.popleft()
        
        # Queue chunk for processing
        await self.processing_queue.put({
            'data': chunk_data,
            'timestamp': time.time(),
            'session_id': self.session_id
        })

    async def _process_chunks(self) -> None:
        """Background task to process audio chunks"""
        while self.is_streaming:
            try:
                # Wait for chunk with timeout
                chunk = await asyncio.wait_for(
                    self.processing_queue.get(), 
                    timeout=1.0
                )
                
                # Process chunk asynchronously
                asyncio.create_task(self._transcribe_chunk(chunk))
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.bind(tag=TAG).error(f"Chunk processing error: {str(e)}")

    async def _transcribe_chunk(self, chunk: dict) -> None:
        """
        Transcribe a single audio chunk
        
        Args:
            chunk: Dict containing audio data and metadata
        """
        try:
            start_time = time.time()
            
            # Convert PCM to WAV format for OpenAI API
            wav_data = self._pcm_to_wav(chunk['data'])
            
            # Prepare API request
            headers = {
                "Authorization": f"Bearer {self.api_key}",
            }
            
            files = {
                'file': ('chunk.wav', wav_data, 'audio/wav'),
                'model': (None, self.model),
                'response_format': (None, 'json'),
                'language': (None, self.language)
            }
            
            # Make async request (using thread pool to avoid blocking)
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(self.api_url, headers=headers, files=files, timeout=10)
            )
            
            if response.status_code == 200:
                result = response.json()
                text = result.get('text', '').strip()
                
                if text:
                    # Call all registered callbacks with partial result
                    for callback in self.result_callbacks:
                        await self._safe_callback(callback, text, False)
                    
                    process_time = time.time() - start_time
                    logger.bind(tag=TAG).debug(
                        f"Chunk transcribed: '{text}' (took {process_time:.2f}s)"
                    )
            else:
                logger.bind(tag=TAG).error(
                    f"API error {response.status_code}: {response.text}"
                )
                
        except Exception as e:
            logger.bind(tag=TAG).error(f"Chunk transcription error: {str(e)}")

    async def _safe_callback(self, callback: Callable, text: str, is_final: bool) -> None:
        """Safely execute callback without blocking"""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(text, is_final)
            else:
                callback(text, is_final)
        except Exception as e:
            logger.bind(tag=TAG).error(f"Callback error: {str(e)}")

    def _pcm_to_wav(self, pcm_data: bytes) -> io.BytesIO:
        """
        Convert PCM data to WAV format
        
        Args:
            pcm_data: Raw PCM audio bytes
            
        Returns:
            BytesIO: WAV formatted audio data
        """
        wav_buffer = io.BytesIO()
        
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(self.channels)
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(pcm_data)
        
        wav_buffer.seek(0)
        return wav_buffer

    async def finalize_streaming(self, final_callback: Optional[Callable[[str], None]] = None) -> str:
        """
        Finalize streaming session and get complete transcript
        
        Args:
            final_callback: Optional callback for final complete transcript
            
        Returns:
            str: Complete final transcript
        """
        try:
            self.is_streaming = False
            
            # Process any remaining audio in buffer
            if len(self.audio_buffer) > 0:
                remaining_data = bytes(self.audio_buffer)
                if len(remaining_data) > self.sample_rate:  # At least 0.5 seconds
                    final_chunk = {
                        'data': remaining_data,
                        'timestamp': time.time(),
                        'session_id': self.session_id
                    }
                    await self._transcribe_chunk(final_chunk)
            
            # Clear buffers
            self.audio_buffer.clear()
            
            # Wait a moment for final processing
            await asyncio.sleep(0.5)
            
            # Notify callbacks that streaming is complete
            for callback in self.result_callbacks:
                await self._safe_callback(callback, "", True)
            
            self.result_callbacks.clear()
            
            logger.bind(tag=TAG).info(f"Streaming finalized for session: {self.session_id}")
            return "Streaming session completed"
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"Finalization error: {str(e)}")
            return ""

    async def speech_to_text(self, opus_data: List[bytes], session_id: str, audio_format="opus") -> Tuple[Optional[str], Optional[str]]:
        """
        Legacy compatibility method - converts to streaming mode
        
        Args:
            opus_data: List of audio chunks
            session_id: Session identifier
            audio_format: Audio format
            
        Returns:
            Tuple of (transcript, file_path)
        """
        try:
            # Convert opus to PCM if needed
            if audio_format == "opus":
                pcm_data = self.decode_opus(opus_data)
            else:
                pcm_data = b''.join(opus_data) if isinstance(opus_data, list) else opus_data
            
            # Process as streaming chunks
            results = []
            
            def collect_result(text: str, is_final: bool):
                if text.strip():
                    results.append(text.strip())
            
            await self.start_streaming(session_id, collect_result)
            
            # Add all audio data
            await self.add_audio_chunk(pcm_data)
            
            # Finalize and get results
            await self.finalize_streaming()
            
            # Combine results
            final_text = ' '.join(results) if results else ""
            
            logger.bind(tag=TAG).info(f"Legacy mode completed: '{final_text}'")
            return final_text, None
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"Legacy speech_to_text error: {str(e)}")
            return None, None

    def get_streaming_stats(self) -> dict:
        """Get streaming performance statistics"""
        return {
            "is_streaming": self.is_streaming,
            "buffer_size": len(self.audio_buffer),
            "chunk_duration": self.chunk_duration,
            "overlap_duration": self.overlap_duration,
            "queue_size": self.processing_queue.qsize() if hasattr(self.processing_queue, 'qsize') else 0,
            "active_callbacks": len(self.result_callbacks)
        }