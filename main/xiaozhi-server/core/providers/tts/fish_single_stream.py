import os
import queue
import asyncio
import traceback
import time
from pathlib import Path
from config.logger import setup_logging
from core.utils.tts import MarkdownCleaner
from core.providers.tts.base import TTSProviderBase
from core.utils import opus_encoder_utils, textUtils
from core.providers.tts.dto.dto import SentenceType, ContentType, InterfaceType, TTSAudioDTO, MessageTag
from fishaudio import FishAudio, TTSConfig

TAG = __name__
logger = setup_logging()


class TTSProvider(TTSProviderBase):

    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        
        # Mark as streaming interface
        self.interface_type = InterfaceType.SINGLE_STREAM

        self.model = config.get("model", "speech-1.6")
        self.reference_id = config.get("reference_id")

        self.format = config.get("response_format", "pcm")
        self.sample_rate = config.get("sample_rate", 16000)
        self.audio_file_type = config.get("response_format", "pcm")
        self.api_key = config.get("api_key", "YOUR_API_KEY")
        if self.api_key is None:
            raise ValueError("FishSpeech API key is required")
        self._client = FishAudio(api_key=self.api_key)
        
        self.normalize = str(config.get("normalize", True)).lower() in (
            "true",
            "1",
            "yes",
        )

        # Handle empty string cases
        channels = config.get("channels", "1")
        rate = config.get("rate", "44100")
        max_new_tokens = config.get("max_new_tokens", "1024")
        chunk_length = config.get("chunk_length", "200")

        self.channels = int(channels) if channels else 1
        self.rate = int(rate) if rate else 44100
        self.max_new_tokens = int(max_new_tokens) if max_new_tokens else 1024
        self.chunk_length = int(chunk_length) if chunk_length else 200

        # Handle empty string cases
        top_p = config.get("top_p", "0.7")
        temperature = config.get("temperature", "0.7")
        repetition_penalty = config.get("repetition_penalty", "1.2")

        self.top_p = float(top_p) if top_p else 0.7
        self.temperature = float(temperature) if temperature else 0.7
        self.repetition_penalty = (
            float(repetition_penalty) if repetition_penalty else 1.2
        )

        self.streaming = str(config.get("streaming", False)).lower() in (
            "true",
            "1",
            "yes",
        )
        self.use_memory_cache = config.get("use_memory_cache", "on")
        self.seed = int(config.get("seed")) if config.get("seed") else None

        # Initialize Opus encoder (sample_rate should match FishSpeech output)
        self.opus_encoder = opus_encoder_utils.OpusEncoderUtils(
            sample_rate=self.sample_rate, channels=1, frame_size_ms=60
        )

        # PCM buffer for accumulating data before encoding
        self.pcm_buffer = bytearray()
        
        # Track if we've sent FIRST for this session
        self._session_started = False
        # Track first chunk time for latency measurement
        self._first_chunk_logged = False

    def tts_text_priority_thread(self):
        """Streaming text processing thread with lifecycle alignment:
        - tts_text_queue FIRST -> tts_audio_queue FIRST (session start)
        - tts_text_queue TEXT (MIDDLE) -> tts_audio_queue MIDDLE (audio chunks)
        - tts_text_queue LAST -> tts_audio_queue LAST (session end)
        """
        while not self.conn.stop_event.is_set():
            try:
                message = self.tts_text_queue.get(timeout=1)
                
                # Handle FIRST - session start
                if message.sentence_type == SentenceType.FIRST:
                    self.conn.client_abort = False
                    # Initialize session parameters
                    self.tts_stop_request = False
                    self.processed_chars = 0
                    self.tts_text_buff = []
                    self.is_first_sentence = True
                    self.tts_audio_first_sentence = True
                    self._first_chunk_logged = False
                    self._session_started = False
                    self.before_stop_play_files.clear()
                    self.pcm_buffer.clear()
                    self.conn._latency_tts_first_text_time = None
                    logger.bind(tag=TAG).debug("TTS session initialized, waiting for text")
                    continue
                
                # Check for abort
                if self.conn.client_abort:
                    logger.bind(tag=TAG).info("Received abort signal, skipping TTS processing")
                    # If session was started, send LAST to close it
                    if self._session_started:
                        self.tts_audio_queue.put(TTSAudioDTO(
                            sentence_type=SentenceType.LAST,
                            audio_data=None,
                            text=None,
                            message_tag=self._message_tag,
                        ))
                        self._session_started = False
                    continue
                
                # Handle TEXT content
                if ContentType.TEXT == message.content_type:
                    self.tts_text_buff.append(message.content_detail)
                    segment_text = self._get_segment_text()
                    if segment_text:
                        # Record TTS first text input time (for latency tracking)
                        if self.conn._latency_tts_first_text_time is None:
                            self.conn._latency_tts_first_text_time = time.time() * 1000
                            logger.bind(tag=TAG).debug("📝 [Latency] TTS received first text")
                        
                        # Process text with streaming TTS
                        self._stream_tts_segment(segment_text)
                
                # Handle FILE content
                elif ContentType.FILE == message.content_type:
                    logger.bind(tag=TAG).info(f"Adding audio file: {message.content_file}")
                    if message.content_file and os.path.exists(message.content_file):
                        self._process_audio_file_stream(
                            message.content_file,
                            callback=lambda audio_data: self.handle_audio_file(audio_data, message.content_detail)
                        )
                
                # Handle LAST - session end
                if message.sentence_type == SentenceType.LAST:
                    # Process remaining text
                    self._process_remaining_text()
                    
                    # Process any pending audio files and send LAST
                    self._process_before_stop_play_files()
                    
                    self._session_started = False
                    self._first_chunk_logged = False
                    logger.bind(tag=TAG).debug("TTS session ended")

            except queue.Empty:
                continue
            except Exception as e:
                logger.bind(tag=TAG).error(
                    f"TTS text processing failed: {str(e)}, type: {type(e).__name__}, stack: {traceback.format_exc()}"
                )

    def _stream_tts_segment(self, text: str):
        """Process a text segment with streaming TTS, sending audio chunks as MIDDLE messages"""
        text = MarkdownCleaner.clean_markdown(text)
        if not text.strip():
            return
        
        logger.bind(tag=TAG).info(f"FishSpeech streaming: {text}")
        start_time = time.time() * 1000
        
        # Calculate bytes per frame for Opus encoding
        frame_bytes = int(
            self.opus_encoder.sample_rate
            * self.opus_encoder.channels
            * self.opus_encoder.frame_size_ms
            / 1000
            * 2  # 16-bit = 2 bytes per sample
        )
        
        try:
            # Get audio stream from FishSpeech
            audio_stream = self._client.tts.stream(
                text=text,
                reference_id=self.reference_id,
                model=self.model,
                config=TTSConfig(
                    format=self.format,
                    sample_rate=self.sample_rate,
                    normalize=self.normalize,
                    latency="balanced",
                ),
            )
            
            # Send FIRST for each text segment (triggers sentence_start on client)
            # This ensures client receives all text segments, not just the first one
            self.tts_audio_queue.put(TTSAudioDTO(
                sentence_type=SentenceType.FIRST,
                audio_data=None,
                text=text,
                message_tag=self._message_tag,
            ))
            self._session_started = True
            
            # Process audio stream chunks
            for chunk in audio_stream:
                # Check for abort during streaming
                if self.conn.client_abort:
                    logger.bind(tag=TAG).info("Abort during TTS streaming, stopping")
                    break
                
                # Log first chunk latency
                if not self._first_chunk_logged:
                    self._first_chunk_logged = True
                    first_chunk_time = time.time() * 1000
                    self.conn.tts_first_chunk_time = first_chunk_time
                    api_latency = (first_chunk_time - start_time) / 1000
                    logger.bind(tag=TAG).info(f"[Latency] TTS API first chunk: {api_latency:.3f}s")
                
                # Add chunk to PCM buffer
                self.pcm_buffer.extend(chunk)
                
                # Encode and send complete frames as MIDDLE messages
                while len(self.pcm_buffer) >= frame_bytes:
                    # Check abort again before processing
                    if self.conn.client_abort:
                        break
                    
                    frame = bytes(self.pcm_buffer[:frame_bytes])
                    del self.pcm_buffer[:frame_bytes]
                    
                    self.opus_encoder.encode_pcm_to_opus_stream(
                        frame, end_of_stream=False, callback=self._handle_opus_middle
                    )
            
            # Flush remaining data (less than one frame)
            if self.pcm_buffer and not self.conn.client_abort:
                self.opus_encoder.encode_pcm_to_opus_stream(
                    bytes(self.pcm_buffer),
                    end_of_stream=True,
                    callback=self._handle_opus_middle,
                )
                self.pcm_buffer.clear()
            
            elapsed = (time.time() * 1000 - start_time) / 1000
            logger.bind(tag=TAG).debug(f"TTS segment completed in {elapsed:.3f}s: {text[:30]}...")
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"FishSpeech streaming error: {e}")
            # On error, clear buffer to avoid corrupted audio
            self.pcm_buffer.clear()

    def _handle_opus_middle(self, opus_data: bytes):
        """Handle encoded Opus data, send as MIDDLE message"""
        if self.conn.client_abort:
            return
        
        logger.bind(tag=TAG).debug(f"Sending opus frame: {len(opus_data)} bytes")
        self.tts_audio_queue.put(TTSAudioDTO(
            sentence_type=SentenceType.MIDDLE,
            audio_data=opus_data,
            text=None,
            message_tag=self._message_tag,
        ))

    def _audio_play_priority_thread(self):
        """Override base class to accumulate all segments into one report.
        
        - Each FIRST still triggers sentence_start on client (for real-time display)
        - But report accumulates all text segments and audio, only reports on LAST
        """
        from core.utils.output_counter import add_device_output
        from core.handle.reportHandle import enqueue_tts_report
        from core.handle.sendAudioHandle import sendAudioMessage
        from core.utils.opus import pack_opus_with_header
        
        # Accumulated text and audio for the entire session (one LLM response)
        session_text_parts = []
        session_audio = []
        session_message_tag = MessageTag.NORMAL
        
        # Track last send future for ordering
        last_send_future = None
        
        while not self.conn.stop_event.is_set():
            text = None
            try:
                try:
                    tts_audio_message = self.tts_audio_queue.get(timeout=0.1)
                    if isinstance(tts_audio_message, TTSAudioDTO):
                        sentence_type = tts_audio_message.sentence_type
                        audio_datas = tts_audio_message.audio_data
                        text = tts_audio_message.text
                        message_tag = tts_audio_message.message_tag
                    elif isinstance(tts_audio_message, tuple):
                        sentence_type = tts_audio_message[0]
                        audio_datas = tts_audio_message[1]
                        text = tts_audio_message[2]
                        message_tag = MessageTag.NORMAL
                    else:
                        logger.bind(tag=TAG).warning(f"Unknown tts_audio_message type: {type(tts_audio_message)}")
                        continue
                except queue.Empty:
                    if self.conn.stop_event.is_set():
                        break
                    continue

                if self.conn.client_abort:
                    logger.bind(tag=TAG).debug("Received abort, reporting accumulated content")
                    # Report accumulated content on abort
                    if session_text_parts and session_audio:
                        full_text = "".join(session_text_parts)
                        enqueue_tts_report(self.conn, full_text, session_audio, session_message_tag)
                        logger.bind(tag=TAG).info(f"Abort report: {full_text[:50]}...")
                    session_text_parts, session_audio = [], []
                    last_send_future = None
                    continue

                # Handle FIRST: accumulate text, don't report yet
                if sentence_type == SentenceType.FIRST:
                    if text:
                        session_text_parts.append(text)
                    session_message_tag = message_tag

                # Handle MIDDLE: accumulate audio
                if isinstance(audio_datas, bytes):
                    audio_with_header = pack_opus_with_header(audio_datas, message_tag)
                    session_audio.append(audio_with_header)

                # Handle LAST: report the entire accumulated session
                if sentence_type == SentenceType.LAST:
                    if session_text_parts or session_audio:
                        full_text = "".join(session_text_parts)
                        if full_text and session_audio:
                            enqueue_tts_report(self.conn, full_text, session_audio, session_message_tag)
                            logger.bind(tag=TAG).info(f"Session report: {full_text[:80]}...")
                    session_text_parts, session_audio = [], []

                # Wait for previous send to complete (maintain order)
                if last_send_future is not None:
                    try:
                        last_send_future.result(timeout=5.0)
                    except Exception as e:
                        logger.bind(tag=TAG).warning(f"Previous audio send timeout: {e}")

                # Send audio to client (async, non-blocking)
                last_send_future = asyncio.run_coroutine_threadsafe(
                    sendAudioMessage(self.conn, sentence_type, audio_datas, text, message_tag),
                    self.conn.loop,
                )

                # Track output
                if self.conn.max_output_size > 0 and text:
                    add_device_output(self.conn.headers.get("device-id"), len(text))

            except Exception as e:
                logger.bind(tag=TAG).error(f"_audio_play_priority_thread error: {text} {e}")

        # On connection close, report remaining accumulated data
        if session_text_parts and session_audio:
            try:
                full_text = "".join(session_text_parts)
                enqueue_tts_report(self.conn, full_text, session_audio, session_message_tag)
                logger.bind(tag=TAG).info(f"Connection close report: {full_text}")
            except Exception as e:
                logger.bind(tag=TAG).warning(f"Connection close report failed: {e}")

    def _process_remaining_text(self):
        """Process any remaining text in buffer"""
        full_text = "".join(self.tts_text_buff)
        remaining_text = full_text[self.processed_chars:]
        if remaining_text:
            segment_text = textUtils.get_string_no_punctuation_or_emoji(remaining_text)
            if segment_text:
                self._stream_tts_segment(segment_text)
                self.processed_chars = len(full_text)

    async def text_to_speak(self, text, output_file):
        """Non-streaming TTS interface (required by base class)
        
        This provider primarily uses streaming, but this method is needed
        for compatibility with base class abstract method.
        """
        text = MarkdownCleaner.clean_markdown(text)
        audio_bytes = self._client.tts.convert(
            text=text,
            reference_id=self.reference_id,
            model=self.model,
            config=TTSConfig(
                format=self.format,
                sample_rate=self.sample_rate,
                normalize=self.normalize,
                latency="balanced",
            )
        )
        if output_file:
            with open(output_file, 'wb') as f:
                f.write(audio_bytes)
        return audio_bytes

    async def close(self):
        """Resource cleanup"""
        await super().close()
        if hasattr(self, "opus_encoder"):
            self.opus_encoder.close()
