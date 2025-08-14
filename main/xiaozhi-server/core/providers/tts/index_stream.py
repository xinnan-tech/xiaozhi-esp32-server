import os
import queue
import asyncio
import traceback
import aiohttp
import requests
import time
from config.logger import setup_logging
from core.utils.tts import MarkdownCleaner
from core.providers.tts.base import TTSProviderBase
from core.utils import opus_encoder_utils, textUtils
from core.providers.tts.dto.dto import SentenceType, ContentType, InterfaceType

TAG = __name__
logger = setup_logging()


class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.interface_type = InterfaceType.SINGLE_STREAM
        self.voice = config.get("voice", "xiao_he")
        if config.get("private_voice"):
            self.voice = config.get("private_voice")
        else:
            self.voice = config.get("voice", "xiao_he")
        self.api_url = config.get("api_url", "http://8.138.114.124:11996/tts")
        self.audio_format = "pcm"
        self.before_stop_play_files = []
        self.segment_count = 0

        # Create Opus encoder Note: interface returns sample rate of 24000
        self.opus_encoder = opus_encoder_utils.OpusEncoderUtils(
            sample_rate=24000, channels=1, frame_size_ms=60
        )

        # Text buffer and PCM buffer
        self.text_buffer = ""
        self.pcm_buffer = bytearray()

    def tts_text_priority_thread(self):
        """Streaming text processing thread"""
        while not self.conn.stop_event.is_set():
            try:
                message = self.tts_text_queue.get(timeout=1)
                if message.sentence_type == SentenceType.FIRST:
                    # Initialize parameters
                    self.tts_stop_request = False
                    self.processed_chars = 0
                    self.tts_text_buff = []
                    self.segment_count = 0
                    self.before_stop_play_files.clear()

                elif ContentType.TEXT == message.content_type:
                    self.tts_text_buff.append(message.content_detail)
                    segment_text = self._get_segment_text()
                    if segment_text:
                        self.to_tts_single_stream(segment_text)

                elif ContentType.FILE == message.content_type:
                    logger.bind(tag=TAG).info(
                        f"Adding audio file to playback queue: {message.content_file}"
                    )

                    if message.content_file and os.path.exists(message.content_file):
                        # Process file audio data first
                        file_audio = self._process_audio_file(
                            message.content_file)
                        self.before_stop_play_files.append(
                            (file_audio, message.content_detail)
                        )

                if message.sentence_type == SentenceType.LAST:
                    # Process remaining text
                    self._process_remaining_text(True)

            except queue.Empty:
                continue
            except Exception as e:
                logger.bind(tag=TAG).error(
                    f"Failed to process TTS text: {str(e)}, type: {type(e).__name__}, stack: {traceback.format_exc()}"
                )

    def _process_remaining_text(self, is_last=False):
        """Process remaining text and generate speech

        Returns:
            bool: Whether text was successfully processed
        """
        full_text = "".join(self.tts_text_buff)
        remaining_text = full_text[self.processed_chars:]
        if remaining_text:
            segment_text = textUtils.get_string_no_punctuation_or_emoji(
                remaining_text)
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
                    f"Speech generation failed {5 - max_repeat_time + 1} times: {text}, error: {e}"
                )

                max_repeat_time -= 1
                if max_repeat_time > 0:
                    logger.bind(tag=TAG).info(
                        f"Speech generation successful: {text}, retried {5 - max_repeat_time} times"
                    )
                else:
                    logger.bind(tag=TAG).error(
                        f"Speech generation failed: {text}, please check network or service status"
                    )

        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to generate TTS file: {e}")
        finally:
            return None

    async def text_to_speak(self, text, is_last):
        """Stream process TTS audio, push audio list only once per sentence"""
        payload = {"text": text, "character": self.voice}
        frame_bytes = int(
            self.opus_encoder.sample_rate
            * self.opus_encoder.channels  # 1
            * self.opus_encoder.frame_size_ms
            / 1000
            * 2
        )  # 16-bit = 2 bytes

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, json=payload, timeout=10) as resp:
                    if resp.status != 200:
                        logger.bind(tag=TAG).error(
                            f"TTS request failed: {resp.status}, {await resp.text()}"
                        )
                        self.tts_audio_queue.put((SentenceType.LAST, [], None))
                        return

                    self.pcm_buffer.clear()
                    opus_datas_cache = []
                    self.tts_audio_queue.put((SentenceType.FIRST, [], text))

                    # Process audio stream data
                    async for chunk in resp.content.iter_any():
                        data = chunk[0] if isinstance(
                            chunk, (list, tuple)) else chunk
                        if not data:
                            continue

                        self.pcm_buffer.extend(data)

                        while len(self.pcm_buffer) >= frame_bytes:
                            frame = bytes(self.pcm_buffer[:frame_bytes])
                            del self.pcm_buffer[:frame_bytes]
                            opus = self.opus_encoder.encode_pcm_to_opus(
                                frame, end_of_stream=False
                            )

                            if opus:
                                if self.segment_count < 10:  # Send first 10 segments directly
                                    self.tts_audio_queue.put(
                                        (SentenceType.MIDDLE, opus, None)
                                    )
                                    self.segment_count += 1
                                else:
                                    opus_datas_cache.extend(opus)

                    # Flush remaining data that doesn't fill a complete frame
                    if self.pcm_buffer:
                        opus = self.opus_encoder.encode_pcm_to_opus(
                            bytes(self.pcm_buffer), end_of_stream=True
                        )

                        if opus:
                            if self.segment_count < 10:  # Send first 10 segments directly
                                # Send directly
                                self.tts_audio_queue.put(
                                    (SentenceType.MIDDLE, opus, None)
                                )
                                self.segment_count += 1
                            else:
                                # Cache subsequent segments
                                opus_datas_cache.extend(opus)

                        self.pcm_buffer.clear()

                    # If not in first 10 segments, send cached data
                    if self.segment_count >= 10 and opus_datas_cache:
                        self.tts_audio_queue.put(
                            (SentenceType.MIDDLE, opus_datas_cache, None)
                        )

                    # If this is the last segment, audio acquisition complete
                    if is_last:
                        self._process_before_stop_play_files()

        except Exception as e:
            logger.bind(tag=TAG).error(f"TTS request exception: {e}")
            self.tts_audio_queue.put((SentenceType.LAST, [], None))

    async def close(self):
        """Resource cleanup"""
        await super().close()
        if hasattr(self, "opus_encoder"):
            self.opus_encoder.close()

    def to_tts(self, text: str) -> list:
        """Non-streaming TTS processing for testing and saving audio files

        Args:
            text: Text to convert

        Returns:
            list: Returns opus-encoded audio data list
        """
        start_time = time.time()
        text = MarkdownCleaner.clean_markdown(text)
        payload = {"text": text, "character": self.character}

        try:
            with requests.post(self.api_url, json=payload, timeout=5) as response:
                if response.status_code != 200:
                    logger.bind(tag=TAG).error(
                        f"TTS request failed: {response.status_code}, {response.text}"
                    )
                    return []

                logger.info(
                    f"TTS request successful: {text}, time cost: {time.time() - start_time} seconds")

                # Use opus encoder to process PCM data
                opus_datas = []
                pcm_data = response.content

                # Calculate bytes per frame
                frame_bytes = int(
                    self.opus_encoder.sample_rate
                    * self.opus_encoder.channels
                    * self.opus_encoder.frame_size_ms
                    / 1000
                    * 2
                )

                # Process PCM data frame by frame
                for i in range(0, len(pcm_data), frame_bytes):
                    frame = pcm_data[i: i + frame_bytes]
                    if len(frame) < frame_bytes:
                        # Last frame might be insufficient, pad with zeros
                        frame = frame + b"\x00" * (frame_bytes - len(frame))

                    opus = self.opus_encoder.encode_pcm_to_opus(
                        frame, end_of_stream=(i + frame_bytes >= len(pcm_data))
                    )

                    if opus:
                        opus_datas.extend(opus)

                return opus_datas

        except Exception as e:
            logger.bind(tag=TAG).error(f"TTS request exception: {e}")
            return []
