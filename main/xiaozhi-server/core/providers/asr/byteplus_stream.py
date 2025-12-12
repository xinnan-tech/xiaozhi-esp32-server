"""
BytePlus Streaming ASR Provider

Based on VAD stream architecture with FIRST/MIDDLE/LAST messages.
WebSocket connection is reused for the entire session.
Reference: https://docs.byteplus.com/en/docs/byteplusvoice/asrstreaming
"""

import json
import gzip
import uuid
import asyncio
import time
from typing import Optional, Tuple, List
from queue import Empty

from core.providers.asr.base import ASRProviderBase
from core.providers.asr.dto import ASRMessageType, ASRInputMessage, InterfaceType
from config.logger import setup_logging

try:
    import websockets
except ImportError:
    websockets = None

TAG = __name__
logger = setup_logging()


# ============================================================================
# Custom Exceptions
# Reference: https://docs.byteplus.com/en/docs/byteplusvoice/asrstreaming
# ============================================================================

class ASRError(Exception):
    """Base exception for ASR errors"""
    pass


class ASRParseError(ASRError):
    """Failed to parse response"""
    pass


class ASRResponseError(ASRError):
    """Server returned an error response"""
    def __init__(self, code: int, message: str = ""):
        self.code = code
        super().__init__(f"ASR error {code}: {message}")


# BytePlus specific error codes
class ASRInvalidParamsError(ASRResponseError):
    """Invalid request parameters (code 45000001)"""
    def __init__(self): super().__init__(45000001, "Invalid request parameters")


class ASREmptyAudioError(ASRResponseError):
    """Empty audio (code 45000002)"""
    def __init__(self): super().__init__(45000002, "Empty audio")


class ASRTimeoutError(ASRResponseError):
    """Packet waiting timeout (code 45000081)"""
    def __init__(self): super().__init__(45000081, "Packet waiting timeout")


class ASRAudioFormatError(ASRResponseError):
    """Incorrect audio format (code 45000151)"""
    def __init__(self): super().__init__(45000151, "Incorrect audio format")


class ASRServerBusyError(ASRResponseError):
    """Server busy (code 55000031)"""
    def __init__(self): super().__init__(55000031, "Server busy")


ASR_ERROR_MAP = {
    45000001: ASRInvalidParamsError,
    45000002: ASREmptyAudioError,
    45000081: ASRTimeoutError,
    45000151: ASRAudioFormatError,
    55000031: ASRServerBusyError,
}


# ============================================================================
# ASR Provider
# ============================================================================

class ASRProvider(ASRProviderBase):
    """BytePlus Streaming ASR with VAD integration
    
    WebSocket connection is established once per session and reused.
    Each speech segment uses sequence number to distinguish.
    """

    RESOURCE_ID = "volc.bigasr.sauc.duration"
    WS_URL = "wss://voice.ap-southeast-1.bytepluses.com/api/v3/sauc/bigmodel"
    
    # Audio config for Full Client Request
    AUDIO_CONFIG = {
        "audio": {
            "format": "pcm",
            "codec": "raw",
            "rate": 16000,
            "bits": 16,
            "channel": 1,
            "sample_rate": 16000,
        },
        "format": "pcm",
        "request": {
            "model_name": "bigmodel",
            "enable_itn": True,
            "enable_punc": True,
            "enable_ddc": True,
            "show_utterances": False,
            "result_type": "single",
        },
    }

    # ========================================================================
    # Initialization
    # ========================================================================
    
    def __init__(self, config, delete_audio_file):
        super().__init__()
        self.interface_type = InterfaceType.STREAM
        self.config = config
        self.delete_audio_file = delete_audio_file
        
        # Auth config
        self.appid = str(config.get("appid", ""))
        self.access_token = config.get("access_token", "")
        self.output_dir = config.get("output_dir", "tmp/")
        
        # Session state (connection-level)
        self.asr_ws = None
        self._keepalive_task = None
        
        # Segment state (per speech segment)
        self.receive_task = None
        self.is_processing = False
        self._segment_done = False
        self.text = ""
        self.sequence = 0

    # ========================================================================
    # Public Interface
    # ========================================================================

    async def open_audio_channels(self, conn):
        """Open audio channels and establish WebSocket"""
        await super().open_audio_channels(conn)
        await self._ensure_connection()

    async def close(self):
        """Close connection when session ends"""
        self._stop_processing()
        self._stop_keepalive()
        if self.asr_ws:
            await self.asr_ws.close()
            self.asr_ws = None
        logger.bind(tag=TAG).info("ASR connection closed")

    def stop_ws_connection(self):
        """Stop current segment but keep connection"""
        self._stop_processing()

    async def speech_to_text(
        self, opus_data: List[bytes], session_id: str, audio_format: str = "opus"
    ) -> Tuple[Optional[str], Optional[str]]:
        """Legacy interface - return accumulated text"""
        result = self.text
        self.text = ""
        return result, None

    # ========================================================================
    # VAD Message Handler Thread
    # ========================================================================

    def _asr_input_queue_thread(self, conn):
        """Process VAD messages: FIRST/MIDDLE/LAST"""
        logger.bind(tag=TAG).info("BytePlus streaming ASR thread started")
        
        while not conn.stop_event.is_set():
            try:
                message: ASRInputMessage = self.asr_input_queue.get(timeout=0.5)
                self._dispatch_message(conn, message)
            except Empty:
                continue
            except Exception as e:
                logger.bind(tag=TAG).error(f"ASR queue error: {e}")
        
        logger.bind(tag=TAG).info("BytePlus streaming ASR thread stopped")

    def _dispatch_message(self, conn, message: ASRInputMessage):
        """Dispatch message to appropriate handler"""
        handlers = {
            ASRMessageType.FIRST: self._handle_first,
            ASRMessageType.MIDDLE: self._handle_middle,
            ASRMessageType.LAST: self._handle_last,
        }
        handler = handlers.get(message.message_type)
        if handler:
            handler(conn, message)

    def _handle_first(self, conn, message: ASRInputMessage):
        """Handle FIRST - start new speech segment"""
        self._stop_keepalive()  # Stop keepalive before new segment
        self.text = ""
        self._segment_done = False
        self.sequence += 1
        self.is_processing = True
        
        self._run_async(conn, self._start_segment(message.audio_data), timeout=10)

    def _handle_middle(self, conn, message: ASRInputMessage):
        """Handle MIDDLE - send incremental audio"""
        if self.asr_ws and self.is_processing and message.audio_data:
            self._run_async(conn, self._send_audio(message.audio_data), timeout=2)

    def _handle_last(self, conn, message: ASRInputMessage):
        """Handle LAST - finish segment and get result"""
        logger.bind(tag=TAG).info(f"ASR LAST: speech={message.speech_duration:.2f}s")
        
        if self.asr_ws and self.is_processing:
            self._run_async(conn, self._finish_segment(conn, message.audio_data), timeout=10)
            self.is_processing = False

    def _run_async(self, conn, coro, timeout: float):
        """Run coroutine in event loop with timeout"""
        try:
            future = asyncio.run_coroutine_threadsafe(coro, conn.loop)
            future.result(timeout=timeout)
        except Exception as e:
            logger.bind(tag=TAG).error(f"Async operation failed: {e}")

    # ========================================================================
    # Connection Management
    # ========================================================================

    async def _ensure_connection(self) -> bool:
        """Ensure WebSocket connection is established"""
        if self.asr_ws is not None:
            return True
        
        try:
            headers = {
                "X-Api-App-Key": self.appid,
                "X-Api-Access-Key": self.access_token,
                "X-Api-Resource-Id": self.RESOURCE_ID,
                "X-Api-Connect-Id": str(uuid.uuid4()),
            }
            
            self.asr_ws = await websockets.connect(
                self.WS_URL,
                additional_headers=headers,
                max_size=1000000000,
                ping_interval=5,
            )
            logger.bind(tag=TAG).info("ASR WebSocket connected")
            return True
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"WebSocket connection failed: {e}")
            self.asr_ws = None
            return False

    async def _reset_connection(self):
        """Reset connection on error"""
        if self.asr_ws:
            try:
                await self.asr_ws.close()
            except Exception:
                pass
            self.asr_ws = None
        self.is_processing = False

    def _stop_processing(self):
        """Stop current processing"""
        self.is_processing = False
        if self.receive_task:
            self.receive_task.cancel()
            self.receive_task = None

    def _stop_keepalive(self):
        """Stop keepalive task"""
        if self._keepalive_task:
            self._keepalive_task.cancel()
            self._keepalive_task = None

    def _start_keepalive(self, conn):
        """Start keepalive task to send empty frames"""
        self._stop_keepalive()
        self._keepalive_task = asyncio.create_task(self._keepalive_loop())

    async def _keepalive_loop(self):
        """Send empty audio frames to keep connection alive"""
        interval = 5.0  # seconds between keepalive frames
        try:
            while self.asr_ws and not self.is_processing:
                await asyncio.sleep(interval)
                if self.asr_ws and not self.is_processing:
                    try:
                        frame = self._build_audio_frame(b"")
                        await self.asr_ws.send(frame)
                        logger.bind(tag=TAG).debug("Keepalive sent")
                    except Exception as e:
                        logger.bind(tag=TAG).debug(f"Keepalive failed: {e}")
                        break
        except asyncio.CancelledError:
            pass

    # ========================================================================
    # Segment Processing
    # ========================================================================

    async def _start_segment(self, audio_data: bytes):
        """Start a new speech segment with Full Client Request"""
        # Try to start, retry once if connection was stale
        for attempt in range(2):
            if not await self._ensure_connection():
                return
            
            try:
                # Send Full Client Request to start recognition session
                await self.asr_ws.send(self._build_init_request())
                init_res = await asyncio.wait_for(self.asr_ws.recv(), timeout=5)
                self._parse_response(init_res)
                
                logger.bind(tag=TAG).debug(f"Segment {self.sequence} started")
                
                # Start receive task
                if self.receive_task:
                    self.receive_task.cancel()
                self.receive_task = asyncio.create_task(self._receive_results())
                
                # Send first audio
                if audio_data:
                    await self._send_audio(audio_data)
                return  # Success
                
            except websockets.ConnectionClosed as e:
                logger.bind(tag=TAG).warning(f"Connection stale, reconnecting... ({e.code})")
                self.asr_ws = None
                # Will retry with new connection
            except Exception as e:
                logger.bind(tag=TAG).error(f"Start segment failed: {e}")
                await self._reset_connection()
                return

    async def _send_audio(self, audio_data: bytes):
        """Send audio frame (never sends is_last to keep connection alive)"""
        if not self.asr_ws:
            return
        
        try:
            frame = self._build_audio_frame(audio_data)
            await self.asr_ws.send(frame)
        except Exception as e:
            logger.bind(tag=TAG).error(f"Send audio failed: {e}")
            await self._reset_connection()

    async def _finish_segment(self, conn, audio_data: bytes):
        """Finish segment and process result"""
        from core.handle.receiveAudioHandle import startToChat
        from core.utils.util import remove_punctuation_and_length
        from core.handle.reportHandle import enqueue_asr_report
        
        try:
            # Send last audio (without is_last flag to keep connection alive)
            if audio_data:
                await self._send_audio(audio_data)
            
            # Signal receive task to finish with timeout
            self._segment_done = True
            
            # Wait for receive task to complete (will timeout after no response)
            if self.receive_task:
                try:
                    await asyncio.wait_for(self.receive_task, timeout=3.0)
                except asyncio.TimeoutError:
                    pass
                except asyncio.CancelledError:
                    pass
                finally:
                    self.receive_task = None
            
            logger.bind(tag=TAG).info(f"ASR complete: '{self.text}'")
            
            # Process result
            if self.text:
                text = self.text
                self.text = ""
                
                text_len, _ = remove_punctuation_and_length(text)
                if text_len > 0:
                    enhanced_text = self._build_enhanced_text(text, None)
                    await startToChat(conn, enhanced_text)
                    enqueue_asr_report(conn, enhanced_text, [], report_time=int(time.time()))
            
            # Start keepalive to maintain connection
            self._start_keepalive(conn)
                    
        except Exception as e:
            logger.bind(tag=TAG).error(f"Finish segment failed: {e}")
            # Still try to start keepalive on error
            self._start_keepalive(conn)

    async def _receive_results(self):
        """Receive ASR results with timeout-based completion detection
        
        No is_last frame sent, so we detect completion by:
        - 1 second timeout with no new response after segment_done
        - Before segment_done: wait indefinitely for responses
        """
        self._segment_done = False
        idle_timeout = 1.0  # seconds without response after segment_done = complete
        
        try:
            while self.asr_ws and self.is_processing:
                try:
                    if self._segment_done:
                        # After LAST message, use timeout to detect completion
                        response = await asyncio.wait_for(self.asr_ws.recv(), timeout=idle_timeout)
                    else:
                        # Before LAST message, wait indefinitely
                        response = await self.asr_ws.recv()
                    
                    payload = self._parse_response(response)
                    
                    # BytePlus returns full text (not incremental), just update
                    result = payload.get("result", {})
                    if "text" in result:
                        self.text = result["text"]
                        logger.bind(tag=TAG).debug(f"ASR text: '{self.text}'")
                        
                except asyncio.TimeoutError:
                    # No response for idle_timeout after segment done = complete
                    logger.bind(tag=TAG).debug("ASR segment complete (idle timeout)")
                    return
                except ASREmptyAudioError:
                    continue
                except (ASRParseError, ASRResponseError) as e:
                    logger.bind(tag=TAG).warning(f"ASR error: {e}")
                    break
                except websockets.ConnectionClosed as e:
                    logger.bind(tag=TAG).warning(f"WebSocket closed: {e.code} {e.reason}")
                    self.asr_ws = None
                    return
                    
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.bind(tag=TAG).error(f"Receive error: {e}")

    # ========================================================================
    # Protocol Helpers
    # ========================================================================

    def _build_init_request(self) -> bytes:
        """Build Full Client Request for initialization"""
        payload = gzip.compress(json.dumps(self.AUDIO_CONFIG).encode())
        header = self._make_header(msg_type=0x01, flags=0x00)
        
        request = bytearray(header)
        request.extend(len(payload).to_bytes(4, "big"))
        request.extend(payload)
        return bytes(request)

    def _build_audio_frame(self, audio_data: bytes) -> bytes:
        """Build audio frame for sending (never is_last to keep connection alive)"""
        payload = gzip.compress(audio_data) if audio_data else b""
        header = self._make_header(msg_type=0x02, flags=0x00)  # flags=0 always
        
        frame = bytearray(header)
        frame.extend(len(payload).to_bytes(4, "big"))
        frame.extend(payload)
        return bytes(frame)

    def _make_header(self, msg_type: int, flags: int) -> bytes:
        """Build 4-byte protocol header"""
        return bytes([
            0x11,                    # version=1, header_size=1
            (msg_type << 4) | flags, # message type and flags
            0x11,                    # serial=json, compress=gzip
            0x00,                    # reserved
        ])

    def _parse_response(self, res: bytes) -> dict:
        """Parse response, raise exception on error"""
        if len(res) < 4:
            raise ASRParseError("Response too short")
        
        msg_type = res[1] >> 4
        
        # Error response
        if msg_type == 0x0F:
            code = int.from_bytes(res[4:8], "big")
            
            # Check known error codes
            if code in ASR_ERROR_MAP:
                raise ASR_ERROR_MAP[code]()
            
            # Internal server error range (550xxxxx)
            if 55000000 <= code < 56000000:
                raise ASRResponseError(code, "Internal server error")
            
            raise ASRResponseError(code, "Unknown error")
        
        # Normal response
        try:
            return json.loads(res[12:].decode())
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise ASRParseError(f"JSON parse failed: {e}")
