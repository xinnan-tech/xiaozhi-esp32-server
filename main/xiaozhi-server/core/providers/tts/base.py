import os
import re
import queue
import uuid
import asyncio
import threading
from core.utils import p3
from datetime import datetime
from core.utils import textUtils
from abc import ABC, abstractmethod
from config.logger import setup_logging
from core.utils.util import audio_to_data, audio_bytes_to_data
from core.utils.tts import MarkdownCleaner
from core.utils.output_counter import add_device_output
from core.handle.reportHandle import enqueue_tts_report
from core.handle.sendAudioHandle import sendAudioMessage
from core.providers.tts.dto.dto import (
    TTSMessageDTO,
    SentenceType,
    ContentType,
    InterfaceType,
)
import traceback

TAG = __name__
logger = setup_logging()

class TTSProviderBase(ABC):
    def __init__(self, config, delete_audio_file):
        self.interface_type = InterfaceType.NON_STREAM
        self.conn = None
        self.tts_timeout = 10
        self.delete_audio_file = delete_audio_file
        self.audio_file_type = "wav"
        self.output_file = config.get("output_dir", "tmp/")
        self.tts_text_queue = queue.Queue()
        self.tts_audio_queue = queue.Queue()
        self.tts_audio_first_sentence = True
        self.before_stop_play_files = []
        self.tts_text_buff = []
        self.punctuations = (
            "。",
            "？",
            "?",
            "！",
            "!",
            "；",
            ";",
            "：",
            "~",
        )
        self.first_sentence_punctuations = (
            "，",
            "～",
            "~",
            "、",
            ",",
            "。",
            "？",
            "?",
            "！",
            "!",
            "；",
            ";",
            "：",
        )
        self.tts_stop_request = False
        self.processed_chars = 0
        self.is_first_sentence = True

    def generate_filename(self, extension=".wav"):
        return os.path.join(
            self.output_file,
            f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}",
        )

    def to_tts(self, text):
        text = MarkdownCleaner.clean_markdown(text)
        max_repeat_time = 5
        if self.delete_audio_file:
            # Files that need to be deleted are directly converted to audio data
            while max_repeat_time > 0:
                try:
                    audio_bytes = asyncio.run(self.text_to_speak(text, None))
                    if audio_bytes:
                        audio_datas, _ = audio_bytes_to_data(
                            audio_bytes, file_type=self.audio_file_type, is_opus=True
                        )
                        return audio_datas
                    else:
                        max_repeat_time -= 1
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
            return None
        else:
            tmp_file = self.generate_filename()
            try:
                while not os.path.exists(tmp_file) and max_repeat_time > 0:
                    try:
                        asyncio.run(self.text_to_speak(text, tmp_file))
                    except Exception as e:
                        logger.bind(tag=TAG).warning(
                            f"Speech generation failed {5 - max_repeat_time + 1} times: {text}, error: {e}"
                        )
                        # If execution unsuccessful, delete file
                        if os.path.exists(tmp_file):
                            os.remove(tmp_file)
                        max_repeat_time -= 1
                        
                if max_repeat_time > 0:
                    logger.bind(tag=TAG).info(
                        f"Speech generation successful: {text}:{tmp_file}, retried {5 - max_repeat_time} times"
                    )
                else:
                    logger.bind(tag=TAG).error(
                        f"Speech generation failed: {text}, please check network or service status"
                    )
                return tmp_file
            except Exception as e:
                logger.bind(tag=TAG).error(f"Failed to generate TTS file: {e}")
                return None

    @abstractmethod
    async def text_to_speak(self, text, output_file):
        pass

    def audio_to_pcm_data(self, audio_file_path):
        """Convert audio file to PCM encoding"""
        return audio_to_data(audio_file_path, is_opus=False)

    def audio_to_opus_data(self, audio_file_path):
        """Convert audio file to Opus encoding"""
        return audio_to_data(audio_file_path, is_opus=True)

    def tts_one_sentence(
        self,
        conn,
        content_type,
        content_detail=None,
        content_file=None,
        sentence_id=None,
    ):
        """Send one sentence"""
        if not sentence_id:
            if conn.sentence_id:
                sentence_id = conn.sentence_id
            else:
                sentence_id = str(uuid.uuid4().hex)
                conn.sentence_id = sentence_id

        # For single sentence text, perform segmentation processing
        segments = re.split(r"([。！？!?；;\n])", content_detail)
        for seg in segments:
            self.tts_text_queue.put(
                TTSMessageDTO(
                    sentence_id=sentence_id,
                    sentence_type=SentenceType.MIDDLE,
                    content_type=content_type,
                    content_detail=seg,
                    content_file=content_file,
                )
            )

    async def open_audio_channels(self, conn):
        self.conn = conn
        self.tts_timeout = conn.config.get("tts_timeout", 10)
        # TTS processing thread
        self.tts_priority_thread = threading.Thread(
            target=self.tts_text_priority_thread, daemon=True
        )
        self.tts_priority_thread.start()
        # Audio playback processing thread
        self.audio_play_priority_thread = threading.Thread(
            target=self._audio_play_priority_thread, daemon=True
        )
        self.audio_play_priority_thread.start()
        # Default is non-streaming processing mode
        # Override in subclass for streaming processing mode

    def tts_text_priority_thread(self):
        while not self.conn.stop_event.is_set():
            try:
                message = self.tts_text_queue.get(timeout=1)
                if message.sentence_type == SentenceType.FIRST:
                    self.conn.client_abort = False
                    
                if self.conn.client_abort:
                    logger.bind(tag=TAG).info("Received interrupt signal, terminating TTS text processing thread")
                    continue
                    
                if message.sentence_type == SentenceType.FIRST:
                    # Initialize parameters
                    self.tts_stop_request = False
                    self.processed_chars = 0
                    self.tts_text_buff = []
                    self.is_first_sentence = True
                    self.tts_audio_first_sentence = True
                    
                elif ContentType.TEXT == message.content_type:
                    self.tts_text_buff.append(message.content_detail)
                    segment_text = self._get_segment_text()
                    if segment_text:
                        if self.delete_audio_file:
                            audio_datas = self.to_tts(segment_text)
                            if audio_datas:
                                self.tts_audio_queue.put(
                                    (message.sentence_type, audio_datas, segment_text)
                                )
                        else:
                            tts_file = self.to_tts(segment_text)
                            if tts_file:
                                audio_datas = self._process_audio_file(tts_file)
                                self.tts_audio_queue.put(
                                    (message.sentence_type, audio_datas, segment_text)
                                )

                elif ContentType.FILE == message.content_type:
                    self._process_remaining_text()
                    tts_file = message.content_file
                    if tts_file and os.path.exists(tts_file):
                        audio_datas = self._process_audio_file(tts_file)
                        self.tts_audio_queue.put(
                            (message.sentence_type, audio_datas, message.content_detail)
                        )

                if message.sentence_type == SentenceType.LAST:
                    self._process_remaining_text()
                    self.tts_audio_queue.put(
                        (message.sentence_type, [], message.content_detail)
                    )

            except queue.Empty:
                continue
            except Exception as e:
                logger.bind(tag=TAG).error(
                    f"Failed to process TTS text: {str(e)}, type: {type(e).__name__}, stack: {traceback.format_exc()}"
                )
                continue

    def _audio_play_priority_thread(self):
        while not self.conn.stop_event.is_set():
            text = None
            try:
                try:
                    sentence_type, audio_datas, text = self.tts_audio_queue.get(
                        timeout=1
                    )
                except queue.Empty:
                    if self.conn.stop_event.is_set():
                        break
                    continue

                future = asyncio.run_coroutine_threadsafe(
                    sendAudioMessage(self.conn, sentence_type, audio_datas, text),
                    self.conn.loop,
                )
                future.result()
                
                if self.conn.max_output_size > 0 and text:
                    add_device_output(self.conn.headers.get("device-id"), len(text))
                    
                enqueue_tts_report(self.conn, text, audio_datas)
                
            except Exception as e:
                logger.bind(tag=TAG).error(
                    f"audio_play_priority priority_thread: {text} {e}"
                )

    async def start_session(self, session_id):
        pass

    async def finish_session(self, session_id):
        pass

    async def close(self):
        """Resource cleanup method"""
        if hasattr(self, "ws") and self.ws:
            await self.ws.close()

    def _get_segment_text(self):
        # Merge all current text and process unsegmented parts
        full_text = "".join(self.tts_text_buff)
        current_text = full_text[self.processed_chars:]  # Start from unprocessed position
        last_punct_pos = -1
        
        # Choose different punctuation sets based on whether it's the first sentence
        punctuations_to_use = (
            self.first_sentence_punctuations
            if self.is_first_sentence
            else self.punctuations
        )

        for punct in punctuations_to_use:
            pos = current_text.rfind(punct)
            if (pos != -1 and last_punct_pos == -1) or (
                pos != -1 and pos < last_punct_pos
            ):
                last_punct_pos = pos

        if last_punct_pos != -1:
            segment_text_raw = current_text[: last_punct_pos + 1]
            segment_text = textUtils.get_string_no_punctuation_or_emoji(
                segment_text_raw
            )
            self.processed_chars += len(segment_text_raw)  # Update processed character position
            # If it's the first sentence, set flag to False after finding first comma
            if self.is_first_sentence:
                self.is_first_sentence = False
            return segment_text
        elif self.tts_stop_request and current_text:
            segment_text = current_text
            self.is_first_sentence = True  # Reset flag
            return segment_text
        else:
            return None

    def _process_audio_file(self, tts_file):
        """Process audio file and convert to specified format
        
        Args:
            tts_file: Audio file path
            content_detail: Content details
            
        Returns:
            tuple: (sentence_type, audio_datas, content_detail)
        """
        if tts_file.endswith(".p3"):
            audio_datas, _ = p3.decode_opus_from_file(tts_file)
        elif self.conn.audio_format == "pcm":
            audio_datas, _ = self.audio_to_pcm_data(tts_file)
        else:
            audio_datas, _ = self.audio_to_opus_data(tts_file)

        if (
            self.delete_audio_file
            and tts_file is not None
            and os.path.exists(tts_file)
            and tts_file.startswith(self.output_file)
        ):
            os.remove(tts_file)

        return audio_datas

    def _process_before_stop_play_files(self):
        for audio_datas, text in self.before_stop_play_files:
            self.tts_audio_queue.put((SentenceType.MIDDLE, audio_datas, text))
        self.before_stop_play_files.clear()
        self.tts_audio_queue.put((SentenceType.LAST, [], None))

    def _process_remaining_text(self):
        """Process remaining text and generate speech
        
        Returns:
            bool: Whether text was successfully processed
        """
        full_text = "".join(self.tts_text_buff)
        remaining_text = full_text[self.processed_chars:]
        if remaining_text:
            segment_text = textUtils.get_string_no_punctuation_or_emoji(
                remaining_text
            )
            if segment_text:
                if self.delete_audio_file:
                    audio_datas = self.to_tts(segment_text)
                    if audio_datas:
                        self.tts_audio_queue.put(
                            (SentenceType.MIDDLE, audio_datas, segment_text)
                        )
                else:
                    tts_file = self.to_tts(segment_text)
                    audio_datas = self._process_audio_file(tts_file)
                    self.tts_audio_queue.put(
                        (SentenceType.MIDDLE, audio_datas, segment_text)
                    )
                self.processed_chars += len(full_text)
                return True
        return False
