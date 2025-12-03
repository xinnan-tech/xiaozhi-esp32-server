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
from core.providers.tts.dto.dto import SentenceType, ContentType, InterfaceType
from fishaudio import FishAudio, TTSConfig

TAG = __name__
logger = setup_logging()


class TTSProvider(TTSProviderBase):

    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        
        # Mark as streaming interface
        self.interface_type = InterfaceType.SINGLE_STREAM

        self.model = config.get("model", "s1")
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

    def tts_text_priority_thread(self):
        """Streaming text processing thread"""
        while not self.conn.stop_event.is_set():
            try:
                message = self.tts_text_queue.get(timeout=1)
                if message.sentence_type == SentenceType.FIRST:
                    self.conn.client_abort = False
                if self.conn.client_abort:
                    logger.bind(tag=TAG).info("Received abort signal, stopping TTS text processing")
                    continue
                if message.sentence_type == SentenceType.FIRST:
                    # Initialize parameters
                    self.tts_stop_request = False
                    self.processed_chars = 0
                    self.tts_text_buff = []
                    self.is_first_sentence = True
                    self.tts_audio_first_sentence = True
                    self._first_chunk_logged = False
                    self.before_stop_play_files.clear()
                    self.conn._latency_tts_first_text_time = None  # Reset TTS input time
                elif ContentType.TEXT == message.content_type:
                    self.tts_text_buff.append(message.content_detail)
                    segment_text = self._get_segment_text()
                    if segment_text:
                        # Record TTS first text input time (for latency tracking)
                        if not hasattr(self.conn, '_latency_tts_first_text_time') or self.conn._latency_tts_first_text_time is None:
                            import time
                            self.conn._latency_tts_first_text_time = time.time() * 1000
                            logger.bind(tag=TAG).debug("📝 [延迟追踪] TTS首次接收文本")
                        self.to_tts_single_stream(segment_text)

                elif ContentType.FILE == message.content_type:
                    logger.bind(tag=TAG).info(
                        f"Adding audio file to play list: {message.content_file}"
                    )
                    if message.content_file and os.path.exists(message.content_file):
                        self._process_audio_file_stream(
                            message.content_file, 
                            callback=lambda audio_data: self.handle_audio_file(audio_data, message.content_detail)
                        )
                if message.sentence_type == SentenceType.LAST:
                    # Process remaining text
                    self._process_remaining_text_stream(True)
                    self._first_chunk_logged = False

            except queue.Empty:
                continue
            except Exception as e:
                logger.bind(tag=TAG).error(
                    f"TTS text processing failed: {str(e)}, type: {type(e).__name__}, stack: {traceback.format_exc()}"
                )

    def _process_remaining_text_stream(self, is_last=False):
        """Process remaining text and generate speech
        Returns:
            bool: Whether text was successfully processed
        """
        full_text = "".join(self.tts_text_buff)
        remaining_text = full_text[self.processed_chars:]
        if remaining_text:
            segment_text = textUtils.get_string_no_punctuation_or_emoji(remaining_text)
            if segment_text:
                self.to_tts_single_stream(segment_text, is_last)
                self.processed_chars += len(full_text)
            else:
                self._process_before_stop_play_files()
        else:
            self._process_before_stop_play_files()

    def to_tts_single_stream(self, text, is_last=False):
        try:
            max_repeat_time = 5
            text = MarkdownCleaner.clean_markdown(text)
            try:
                asyncio.run(self.text_to_speak(text, is_last))
            except Exception as e:
                logger.bind(tag=TAG).warning(
                    f"TTS generation failed {5 - max_repeat_time + 1} times: {text}, error: {e}"
                )
                max_repeat_time -= 1

            if max_repeat_time > 0:
                logger.bind(tag=TAG).info(
                    f"TTS generation success: {text}, retries: {5 - max_repeat_time}"
                )
            else:
                logger.bind(tag=TAG).error(
                    f"TTS generation failed: {text}, please check network or service"
                )
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to generate TTS: {e}")
        finally:
            return None

    async def text_to_speak(self, text, is_last):
        """Stream TTS audio processing - encode and send each chunk immediately"""
        logger.bind(tag=TAG).info(f"FishSpeech streaming synthesize: {text}")
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

            self.pcm_buffer.clear()
            # Notify that a new sentence is starting
            self.tts_audio_queue.put((SentenceType.FIRST, [], text))

            first_chunk_logged = False

            # Process audio stream - encode and send each chunk immediately
            for chunk in audio_stream:
                # Log first chunk from TTS API
                if not first_chunk_logged:
                    first_chunk_logged = True
                    first_chunk_time = time.time() * 1000
                    self.conn.tts_first_chunk_time = first_chunk_time
                    api_latency = (first_chunk_time - start_time) / 1000
                    logger.bind(tag=TAG).info(f"[Latency] TTS API首个chunk, 耗时: {api_latency:.3f}s")

                # Add chunk to PCM buffer
                self.pcm_buffer.extend(chunk)

                # Encode and send complete frames immediately
                while len(self.pcm_buffer) >= frame_bytes:
                    frame = bytes(self.pcm_buffer[:frame_bytes])
                    del self.pcm_buffer[:frame_bytes]

                    self.opus_encoder.encode_pcm_to_opus_stream(
                        frame, end_of_stream=False, callback=self.handle_opus
                    )

            # Flush remaining data that's less than one frame
            if self.pcm_buffer:
                self.opus_encoder.encode_pcm_to_opus_stream(
                    bytes(self.pcm_buffer),
                    end_of_stream=True,
                    callback=self.handle_opus,
                )
                self.pcm_buffer.clear()

            # If this is the last segment, process any pending files and signal completion
            if is_last:
                self._process_before_stop_play_files()

        except Exception as e:
            logger.bind(tag=TAG).error(f"FishSpeech streaming error: {e}")
            self.tts_audio_queue.put((SentenceType.LAST, [], None))

    def to_tts(self, text):
        """Non-streaming TTS for compatibility - falls back to accumulating all chunks"""
        logger.bind(tag=TAG).info(f"FishSpeech synthesize text: {text}")
        start_time = time.time()
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
        
        logger.bind(tag=TAG).info(f"TTS non-streaming duration: {time.time() - start_time} seconds")
        return audio_bytes

    async def close(self):
        """Resource cleanup"""
        await super().close()
        if hasattr(self, "opus_encoder"):
            self.opus_encoder.close()
