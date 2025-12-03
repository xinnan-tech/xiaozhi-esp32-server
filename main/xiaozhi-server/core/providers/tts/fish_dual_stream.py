"""
Fish Audio Dual Stream TTS Implementation

Based on native WebSocket API (wss://api.fish.audio/v1/tts/live), supporting:
1. Pre-connection optimization: establish WebSocket connection before LLM output
2. Session lifecycle management: start/stop events for each dialogue round
3. FlushEvent + Chunk strategy: force audio generation at punctuation marks
4. Lightweight interruption: send stop event without closing connection

Reference: https://docs.fish.audio/api-reference/endpoint/websocket/tts-live
"""

import os
import uuid
import queue
import asyncio
import traceback
import ormsgpack
import websockets

from core.utils.tts import MarkdownCleaner
from core.utils import opus_encoder_utils
from core.utils.util import check_model_key
from core.providers.tts.base import TTSProviderBase
from core.providers.tts.dto.dto import SentenceType, ContentType, InterfaceType
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()

# Fish Audio WebSocket API endpoint
FISH_WS_URL = "wss://api.fish.audio/v1/tts/live"


class TTSProvider(TTSProviderBase):
    """Fish Audio Dual Stream TTS Implementation using native WebSocket API"""

    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        
        # Mark as dual stream interface
        self.interface_type = InterfaceType.DUAL_STREAM
        
        # Fish Audio configuration
        self.api_key = config.get("api_key")
        if not self.api_key:
            raise ValueError("Fish Audio API key is required")
        
        self.model = config.get("model", "s1")
        self.reference_id = config.get("reference_id")
        self.format = config.get("response_format", "pcm")
        self.sample_rate = int(config.get("sample_rate", 16000))
        self.audio_file_type = self.format
        self.latency_mode = config.get("latency_mode", "balanced")
        self.chunk_length = int(config.get("chunk_length", 200))
        self.top_p = float(config.get("top_p", 0.7))
        self.temperature = float(config.get("temperature", 0.7))
        
        self.normalize = str(config.get("normalize", True)).lower() in (
            "true", "1", "yes"
        )
        
        # WebSocket connection state
        self.ws = None
        self._ws_connected = False
        self._session_active = False
        self._monitor_task = None
        
        # Opus encoder (PCM -> Opus)
        self.opus_encoder = opus_encoder_utils.OpusEncoderUtils(
            sample_rate=self.sample_rate, channels=1, frame_size_ms=60
        )
        
        # Text buffer for current session (supports both LLM and voice_opening/closing)
        self._session_text_buffer = []
        self._first_sent = False
                
        # Check API Key
        model_key_msg = check_model_key("TTS", self.api_key)
        if model_key_msg:
            logger.bind(tag=TAG).error(model_key_msg)
        
    async def open_audio_channels(self, conn):
        """
        Override: establish WebSocket pre-connection
        
        Connect to Fish Audio WebSocket before LLM starts generating,
        reducing connection delay for the first TTS request.
        """
        try:
            await super().open_audio_channels(conn)
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to open audio channels: {str(e)}")
            self.ws = None
            self._ws_connected = False 
            raise

    async def _ensure_connection(self, max_retries: int = 2):
        """Ensure WebSocket connection is established with retry logic"""
        if self.ws and self._ws_connected:
            logger.bind(tag=TAG).debug("Using existing WebSocket connection")
            return
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "model": self.model,
        }
        
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                logger.bind(tag=TAG).info(f"Establishing WebSocket connection (attempt {attempt + 1}/{max_retries + 1})...")
                
                self.ws = await websockets.connect(
                    FISH_WS_URL,
                    additional_headers=headers,
                    max_size=10 * 1024 * 1024,  # 10MB max message size
                    open_timeout=10,  # 10s connection timeout
                    close_timeout=5,  # 5s close timeout
                )
                self._ws_connected = True
                
                # Start response monitor task
                if self._monitor_task is None or self._monitor_task.done():
                    logger.bind(tag=TAG).info("Starting WebSocket monitor task...")
                    self._monitor_task = asyncio.create_task(self._monitor_ws_response())
                
                return  # Success
                
            except Exception as e:
                last_error = e
                logger.bind(tag=TAG).warning(f"WebSocket connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries:
                    await asyncio.sleep(0.5)  # Brief delay before retry
        
        # All retries failed
        raise last_error


    def tts_text_priority_thread(self):
        """
        Override: dual stream TTS text processing thread
        
        Manages session lifecycle based on FIRST/LAST signals.
        
        Key insights from Fish Audio WebSocket API:
        1. stop_event triggers WebSocket close, so only use it for interruptions
        2. For normal LAST, send flush event to force remaining text generation
        3. Fish has no multi-context management, interruption requires reconnection
        """
        while not self.conn.stop_event.is_set():
            try:
                message = self.tts_text_queue.get(timeout=1)
                logger.bind(tag=TAG).debug(
                    f"Received TTS task | {message.sentence_type.name} | {message.content_type.name}"
                )

                if message.sentence_type == SentenceType.FIRST:
                    # ========== New dialogue round starts ==========
                    self.conn.client_abort = False

                elif self.conn.client_abort:
                    # ========== Interruption ==========
                    # Only send stop event on interruption (this will close the connection)
                    logger.bind(tag=TAG).info("Received interruption, sending stop event")
                    try:
                        future = asyncio.run_coroutine_threadsafe(
                            self._abort_session(),
                            self.conn.loop
                        )
                        future.result()
                    except Exception as e:
                        logger.bind(tag=TAG).error(f"Failed to abort session: {e}")
                    continue
                
                # when user doesn't trigger interruption, start new TTS session
                if message.sentence_type == SentenceType.FIRST:
                    # Start new TTS session
                    try:
                        future = asyncio.run_coroutine_threadsafe(
                            self._start_session(),
                            self.conn.loop
                        )
                        future.result()
                        self.before_stop_play_files.clear()
                    except Exception as e:
                        logger.bind(tag=TAG).error(f"Failed to start session: {e}")
                        continue
                elif ContentType.TEXT == message.content_type:
                    # ========== Text content ==========
                    if message.content_detail:
                        # Accumulate text for reporting (supports voice_opening/closing and LLM content)
                        self._session_text_buffer.append(message.content_detail)
                        
                        try:
                            logger.bind(tag=TAG).debug(
                                f"Sending TTS text: {message.content_detail}"
                            )
                            future = asyncio.run_coroutine_threadsafe(
                                self.text_to_speak(message.content_detail, None),
                                loop=self.conn.loop,
                            )
                            future.result()
                            logger.bind(tag=TAG).debug("TTS text sent successfully")
                        except Exception as e:
                            logger.bind(tag=TAG).error(f"Failed to send TTS text: {e}")
                            continue

                elif ContentType.FILE == message.content_type:
                    # ========== File content ==========
                    logger.bind(tag=TAG).info(
                        f"Adding audio file to playback list: {message.content_file}"
                    )
                    if message.content_file and os.path.exists(message.content_file):
                        # Process file audio data first
                        self._process_audio_file_stream(message.content_file, callback=lambda audio_data: self.handle_audio_file(audio_data, message.content_detail))

                if message.sentence_type == SentenceType.LAST:
                    # ========== Dialogue round ends (normal) ==========
                    # DO NOT send stop event here! Just send flush to force remaining text.
                    # The finish event from Fish will trigger LAST in audio queue.
                    try:
                        future = asyncio.run_coroutine_threadsafe(
                            self._flush_session(),
                            loop=self.conn.loop,
                        )
                        future.result()
                    except Exception as e:
                        logger.bind(tag=TAG).error(f"Failed to flush session: {e}")
                        continue

            except queue.Empty:
                continue
            except Exception as e:
                logger.bind(tag=TAG).error(
                    f"TTS text processing failed: {str(e)}, type: {type(e).__name__}, "
                    f"stack: {traceback.format_exc()}"
                )
        
    async def close(self):
        """Clean up WebSocket resources"""
        self._session_active = False
        self._ws_connected = False
        
        # Cancel monitor task
        if self._monitor_task:
            try:
                self._monitor_task.cancel()
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.bind(tag=TAG).warning(f"Error canceling monitor task: {e}")
            self._monitor_task = None
        
        # Close WebSocket
        if self.ws:
            try:
                await self.ws.close()
            except:
                pass
            self.ws = None
            self._ws_connected = False 
        
        await super().close()

    async def _monitor_ws_response(self):
        """Monitor WebSocket responses - long running task (MessagePack serialization)"""
        try:
            while not self.conn.stop_event.is_set():
                try:
                    if not self.ws:
                        break
                    
                    msg = await self.ws.recv()
                    response = ormsgpack.unpackb(msg)
                    event_type = response.get("event")
                    
                    if event_type == "audio":
                        # Received audio chunk (binary data)
                        audio_data = response.get("audio")
                        if audio_data and not self.conn.client_abort:
                            # 在第一个音频之前发送 FIRST（带当前累积的文本）
                            # 这样后续音频通过 MIDDLE 累积时，enqueue_audio 不会被清空
                            if not self._first_sent:
                                self._first_sent = True
                                report_text = ''.join(self._session_text_buffer) if self._session_text_buffer else None
                                self.tts_audio_queue.put((SentenceType.FIRST, None, report_text))
                            
                            # PCM -> Opus conversion
                            self.opus_encoder.encode_pcm_to_opus_stream(
                                audio_data, end_of_stream=False, callback=self.handle_opus
                            )
                    
                    elif event_type == "finish":
                        logger.bind(tag=TAG).info(f"TTS session finished")
                        # Session completed
                        reason = response.get("reason", "unknown")
                        if reason == "error":
                            logger.bind(tag=TAG).error(f"TTS session error")
                        else:
                            logger.bind(tag=TAG).debug(f"TTS session finished")
                        
                        # Flush remaining opus buffer
                        self.opus_encoder.encode_pcm_to_opus_stream(
                            b'', end_of_stream=True, callback=self.handle_opus
                        )
                        
                        # 发送 LAST 触发客户端 stop 和最终上报
                        # 不再发送 FIRST，避免清空之前累积的音频
                        self.tts_audio_queue.put((SentenceType.LAST, None, None))
                        
                        # 清理状态
                        self._session_text_buffer = []
                        self.conn.tts_MessageText = None
                        
                        self._session_active = False
                        self._process_before_stop_play_files()
                        self.ws = None
                        self._ws_connected = False
                        self._first_sent = False
                        
                except websockets.ConnectionClosed:
                    logger.bind(tag=TAG).warning("WebSocket connection closed")
                    break
                except Exception as e:
                    logger.bind(tag=TAG).error(f"Error in monitor task: {e}")
                    traceback.print_exc()
                    break
            
            # Clean up on exit
            if self.ws:
                try:
                    await self.ws.close()
                except:
                    pass
                self.ws = None
                self._ws_connected = False
                
        finally:
            self._monitor_task = None

    async def _send_event(self, event: dict):
        """Send event to Fish Audio WebSocket using MessagePack serialization"""
        if not self.ws or not self._ws_connected:
            logger.bind(tag=TAG).warning("WebSocket not connected, cannot send event")
            return
        
        try:
            bytes_event = ormsgpack.packb(event)
            await self.ws.send(bytes_event)
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to send event: {e}")
            raise

    async def _start_session(self):
        """
        Start a new TTS session
        """
        # Reset state for new session
        self.opus_encoder.reset_state()
        self._session_text_buffer = []
        self._first_sent = False
        self.conn.sentence_id = uuid.uuid4().hex
        
        try:
            # Ensure connection
            await self._ensure_connection()
            
            # Send start event
            start_event = {
                "event": "start",
                "request": {
                    "text": "",
                    "format": self.format,
                    "sample_rate": self.sample_rate,
                    "chunk_length": self.chunk_length,
                    "latency": self.latency_mode,
                    "normalize": self.normalize,
                    "top_p": self.top_p,
                    "temperature": self.temperature,
                }
            }
            
            if self.reference_id:
                start_event["request"]["reference_id"] = self.reference_id
            
            await self._send_event(start_event)
            self._session_active = True
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to start session: {e}")
            raise

    async def _flush_session(self):
        """
        Flush current TTS session - force generation of remaining text
        
        Send flush event to force Fish Audio to generate audio for any buffered text.
        This does NOT close the connection - the finish event from Fish will do that.
        """
        logger.bind(tag=TAG).debug("Flushing TTS session...")
        
        try:
            if self.ws and self._session_active:
                # Send flush event to force remaining text generation
                flush_event = {"event": "flush"}
                await self._send_event(flush_event)
                logger.bind(tag=TAG).debug("TTS flush event sent")
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to flush session: {e}")

    async def _abort_session(self):
        """
        Abort current TTS session due to interruption
        
        Send stop event which will close the WebSocket connection.
        This is only used when user interrupts the conversation.
        """
        logger.bind(tag=TAG).info("Aborting TTS session due to interruption...")
        
        try:
            if self.ws and self._session_active:
                stop_event = {"event": "stop"}
                await self._send_event(stop_event)
                logger.bind(tag=TAG).info("TTS session stop sent (abort)")
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to abort session: {e}")
        finally:
            # Clean up state
            self._session_active = False
            self._session_text_buffer = []
            self._first_sent = False
            # Connection will be closed by Fish Audio after stop event

            
    async def text_to_speak(self, text, output_file):
        """
        streaming TTS text to Fish Audio WebSocket
        
        """
        logger.bind(tag=TAG).debug(f"Fish Audio TTS: {text}")
        try:
            if self.ws is None:
                logger.bind(tag=TAG).warning("WebSocket not connected, cannot send text")
                return
    
            filtered_text = MarkdownCleaner.clean_markdown(text)
    
            # Send text
            text_event = {"event": "text", "text": filtered_text}
            await self._send_event(text_event)
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to send text: {e}")
            if self.ws:
                try:
                    await self.ws.close()
                except:
                    pass
                self.ws = None
                self._ws_connected = False 
            raise