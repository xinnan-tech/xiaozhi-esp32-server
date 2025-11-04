from __future__ import annotations

"""
ElevenLabs TTS Implementation

Provides WebSocket-based streaming text-to-speech using ElevenLabs' multi-stream API.
Supports multiple concurrent synthesis streams over a single WebSocket connection.
"""

"""
TODO: change api to elevenlabs SDK using streaming API
"""

import asyncio
import base64
import dataclasses
import json
import os
import weakref
from dataclasses import dataclass
from typing import Any, Union

import aiohttp
from typing import Optional

from config.logger import setup_logging
from core.tokenize import SentenceTokenizer, WordTokenizer, blingfire
from core.utils.aio import Chan, cancel_and_wait
from core.utils.short_uuid import shortuuid
from core.utils.http_context import http_session
from core.utils.errors import (
    APIConnectionError,
    APITimeoutError,
    APIStatusError,
)
from core.utils.types import (
    APIConnectOptions,
    DEFAULT_API_CONNECT_OPTIONS,
)

import core.providers.tts.base as tts
from ..emitter import AudioEmitter
from .models import (
    API_BASE_URL,
    DEFAULT_VOICE_ID,
    TTSEncoding,
    TTSModels,
    Voice,
    VoiceSettings,
    WS_INACTIVITY_TIMEOUT,
)

logger = setup_logging()


def _sample_rate_from_format(output_format: TTSEncoding) -> int:
    """Extract sample rate from encoding format string"""
    if output_format.startswith("mp3_"):
        return int(output_format.split("_")[1])
    elif output_format.startswith("pcm_"):
        return int(output_format.split("_")[1])
    elif output_format.startswith("ulaw_"):
        return int(output_format.split("_")[1])
    return 22050  # default


@dataclass
class _TTSOptions:
    """Internal configuration for ElevenLabs TTS"""
    api_key: str
    voice_id: str
    voice_settings: VoiceSettings | None
    model: TTSModels | str
    base_url: str
    encoding: TTSEncoding
    sample_rate: int
    word_tokenizer: WordTokenizer | SentenceTokenizer
    inactivity_timeout: int
    auto_mode: bool
    
    def get_ws_url(self) -> str:
        """Get WebSocket URL for multi-stream API"""
        base = self.base_url.replace("http://", "ws://").replace("https://", "wss://")
        params = [
            f"model_id={self.model}",
            f"output_format={self.encoding}",
        ]
        if self.auto_mode:
            params.append("auto_mode=true")
        params.append(f"inactivity_timeout={self.inactivity_timeout}")
        
        url = f"{base}/text-to-speech/{self.voice_id}/multi-stream-input?"
        url += "&".join(params)
        return url


class TTS(tts.TTS):
    """
    ElevenLabs TTS Provider
    
    Provides high-quality, emotionally rich text-to-speech with voice cloning support.
    Uses multi-stream WebSocket API for efficient concurrent synthesis.
    
    Example:
        tts = elevenlabs.TTS(
            api_key="your-api-key",
            voice_id="voice-id",
            model="eleven_turbo_v2_5",
        )
        
        # Streaming synthesis
        stream = tts.stream()
        stream.push_text("Hello world!")
        stream.end_input()
        
        async for audio in stream:
            # Process audio
            pass
    """
    
    def __init__(
        self,
        *,
        api_key: str | None = None,
        voice_id: str = DEFAULT_VOICE_ID,
        voice_settings: VoiceSettings | None = None,
        model: TTSModels | str = "eleven_multilingual_v2",
        encoding: TTSEncoding = "pcm_16000",
        word_tokenizer: WordTokenizer | SentenceTokenizer | None = None,
        inactivity_timeout: int = WS_INACTIVITY_TIMEOUT,
        auto_mode: Optional[bool] = None,
        base_url: str = API_BASE_URL,
    ) -> None:
        """
        Initialize ElevenLabs TTS.
        
        Args:
            api_key: ElevenLabs API key. If not provided, reads from ELEVEN_API_KEY env var
            voice_id: Voice ID to use (default: Rachel voice)
            voice_settings: Voice settings for fine-tuning quality
            model: TTS model to use (default: "eleven_multilingual_v2")
            encoding: Audio encoding format (default: "pcm_16000")
            word_tokenizer: Word/sentence tokenizer (default: blingfire for auto_mode)
            inactivity_timeout: WebSocket inactivity timeout in seconds
            auto_mode: Enable auto mode for optimized latency (recommended)
            base_url: API base URL (default: https://api.elevenlabs.io/v1)
        """
        sample_rate = _sample_rate_from_format(encoding)
        
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=True),
            sample_rate=sample_rate,
            num_channels=1,
        )
        
        # Validate API key
        elevenlabs_api_key = api_key or os.environ.get("ELEVEN_API_KEY")
        if not elevenlabs_api_key:
            raise ValueError(
                "ElevenLabs API key is required. "
                "Provide via api_key parameter or set ELEVEN_API_KEY environment variable"
            )
        
        # Configure tokenizer
        if not word_tokenizer:
            if auto_mode:
                word_tokenizer = blingfire.SentenceTokenizer()
            else:
                from core.tokenize.basic import WordTokenizer as BasicWordTokenizer
                word_tokenizer = BasicWordTokenizer(ignore_punctuation=False)
        
        # Store options
        self._opts = _TTSOptions(
            api_key=elevenlabs_api_key,
            voice_id=voice_id,
            voice_settings=voice_settings,
            model=model,
            base_url=base_url,
            encoding=encoding,
            sample_rate=sample_rate,
            word_tokenizer=word_tokenizer,
            inactivity_timeout=inactivity_timeout,
            auto_mode=auto_mode,
        )
        self._session = http_session()
        # Connection management
        self._current_connection: _Connection | None = None
        self._connection_lock = asyncio.Lock()
        
        # Track active streams
        self._streams: weakref.WeakSet[SynthesizeStream] = weakref.WeakSet()
    
    @property
    def model(self) -> str:
        """Get the model name"""
        return self._opts.model
    
    @property
    def provider(self) -> str:
        """Get the provider name"""
        return "ElevenLabs"
    
    def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure HTTP session exists"""
        return http_session()
    
    async def current_connection(self) -> _Connection:
        """Get or create the current WebSocket connection"""
        async with self._connection_lock:
            if (
                self._current_connection
                and self._current_connection.is_current
                and not self._current_connection._closed
            ):
                return self._current_connection
            
            # Create new connection
            session = self._ensure_session()
            conn = _Connection(self._opts, session)
            await conn.connect()
            self._current_connection = conn
            return conn
    
    async def list_voices(self) -> list[Voice]:
        """List available voices from ElevenLabs API"""
        session = self._ensure_session()
        url = f"{self._opts.base_url}/voices"
        headers = {"xi-api-key": self._opts.api_key}
        
        async with session.get(url, headers=headers) as resp:
            resp.raise_for_status()
            data = await resp.json()
            
            voices = []
            for voice_data in data.get("voices", []):
                voices.append(
                    Voice(
                        id=voice_data["voice_id"],
                        name=voice_data["name"],
                        category=voice_data["category"],
                    )
                )
            return voices
    
    def stream(self, *, conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS) -> SynthesizeStream:
        """
        Create a streaming synthesis session.
        
        Returns:
            SynthesizeStream for incremental text input
        """
        stream = SynthesizeStream(tts=self, conn_options=conn_options)
        self._streams.add(stream)
        return stream
    
    async def aclose(self) -> None:
        """Close TTS provider and cleanup resources"""
        # Close all active streams
        for stream in list(self._streams):
            await stream.aclose()
        self._streams.clear()
        
        # Close connection
        if self._current_connection:
            await self._current_connection.aclose()
            self._current_connection = None


class SynthesizeStream(tts.SynthesizeStream):
    """Streaming synthesis using WebSocket (multi-stream)"""
    
    def __init__(
        self, *, tts: TTS, conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS
    ) -> None:
        super().__init__(tts=tts, conn_options=conn_options)
        self._tts: TTS = tts
        self._sent_tokenizer_stream = self._tts._opts.word_tokenizer.stream()
    
    async def aclose(self) -> None:
        """Close stream and cleanup"""
        await self._sent_tokenizer_stream.aclose()
        await super().aclose()
    
    async def _run(self, output_emitter: AudioEmitter) -> None:
        """
        Streaming synthesis implementation using multi-stream WebSocket.
        
        This method:
        1. Connects to the shared WebSocket connection
        2. Registers this stream with the connection
        3. Sets up tokenizer
        4. Runs two parallel tasks:
           - _input_task: Reads from input_ch → tokenizer
           - _sentence_task: Tokenizer → Connection (which sends to WebSocket)
        5. The connection's recv loop handles audio data and routes it to this stream's emitter
        """
        opts = self._tts._opts
        request_id = shortuuid()
        context_id = shortuuid()  # Generate context_id upfront for registration
        
        # Initialize output emitter
        output_emitter.initialize(
            request_id=request_id,
            sample_rate=opts.sample_rate,
            num_channels=1,
            stream=True,
        )
        
        # Get shared connection
        try:
            connection = await asyncio.wait_for(
                self._tts.current_connection(), timeout=10
            )
        except asyncio.TimeoutError as e:
            raise APITimeoutError("Could not connect to ElevenLabs", timeout=10) from e
        except Exception as e:
            raise APIConnectionError(f"Could not connect to ElevenLabs: {e}") from e
        
        # Create waiter for completion
        waiter: asyncio.Future[None] = asyncio.get_event_loop().create_future()
        # Register stream with context_id
        connection.register_stream(context_id, output_emitter, waiter)
        
        # Define tasks
        async def _input_task() -> None:
            """Forward input from input_ch to tokenizer"""
            try:
                async for data in self._input_ch:
                    if isinstance(data, self._FlushSentinel):
                        self._sent_tokenizer_stream.flush()
                        continue
                    self._sent_tokenizer_stream.push_text(data)
            finally:
                self._sent_tokenizer_stream.end_input()
        
        async def _sentence_task() -> None:
            """Send tokenized sentences to connection"""
            try:
                async for sentence_ev in self._sent_tokenizer_stream:
                    text = sentence_ev.token
                    formatted_text = f"{text} "  # Always end with space
                    connection.send_content(_SynthesizeContent(context_id, formatted_text))
            finally:
                connection.send_content(_SynthesizeContent(context_id, "", flush=True))
                connection.close_context(context_id)
        
        # Run tasks
        input_t = asyncio.create_task(_input_task(), name="elevenlabs_input")
        sentence_t = asyncio.create_task(_sentence_task(), name="elevenlabs_sentence")
        
        try:
            await waiter
        except asyncio.TimeoutError as e:
            raise TimeoutError("ElevenLabs synthesis timed out") from e
        except Exception as e:
            logger.bind(tag=__name__).error(f"Synthesis error: {e}")
            raise
        finally:
            await cancel_and_wait(input_t, sentence_t)


@dataclass
class _SynthesizeContent:
    """Content to synthesize"""
    context_id: str
    text: str
    flush: bool = False


@dataclass
class _CloseContext:
    """Command to close a context"""
    context_id: str


@dataclass
class _StreamData:
    """Data for a registered stream"""
    emitter: AudioEmitter
    stream: SynthesizeStream | None
    waiter: asyncio.Future[None]
    timeout_timer: asyncio.TimerHandle | None = None


class _Connection:
    """
    Manages a single WebSocket connection with send/recv loops.
    
    Supports multiple concurrent synthesis contexts (multi-stream).
    """
    
    def __init__(self, opts: _TTSOptions, session: aiohttp.ClientSession) -> None:
        self._opts = opts
        self._session = session
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._is_current = True
        self._active_contexts: set[str] = set()
        self._input_queue: Chan[Union[_SynthesizeContent, _CloseContext]] = Chan()
        self._context_data: dict[str, _StreamData] = {}
        self._send_task: asyncio.Task | None = None
        self._recv_task: asyncio.Task | None = None
        self._closed = False
    
    @property
    def is_current(self) -> bool:
        """Check if this connection is current"""
        return self._is_current
    
    def mark_non_current(self) -> None:
        """Mark this connection as no longer current"""
        self._is_current = False
    
    async def connect(self) -> None:
        """Establish WebSocket connection and start send/recv loops"""
        if self._ws or self._closed:
            return
        
        url = self._opts.get_ws_url()
        headers = {"xi-api-key": self._opts.api_key}
        
        try:
            self._ws = await asyncio.wait_for(
                self._session.ws_connect(url, headers=headers),
                timeout=10,
            )
        except asyncio.TimeoutError as e:
            raise APITimeoutError(
                "Connection to ElevenLabs WebSocket timed out",
                timeout=10,
            ) from e
        except aiohttp.ClientError as e:
            raise APIConnectionError(
                f"Failed to connect to ElevenLabs WebSocket: {e}",
                url=url,
            ) from e
        
        self._send_task = asyncio.create_task(self._send_loop(), name="elevenlabs_send")
        self._recv_task = asyncio.create_task(self._recv_loop(), name="elevenlabs_recv")
    
    def register_stream(
        self,
        context_id: str,
        emitter: AudioEmitter,
        done_fut: asyncio.Future[None],
    ) -> None:
        """Register a new synthesis stream"""
        self._context_data[context_id] = _StreamData(
            emitter=emitter,
            stream=None,  # Stream reference not needed
            waiter=done_fut,
        )
    
    def send_content(self, content: _SynthesizeContent) -> None:
        """Send synthesis content to the connection"""
        if self._closed or not self._ws or self._ws.closed:
            raise ConnectionError("WebSocket connection is closed")
        self._input_queue.send_nowait(content)
    
    def close_context(self, context_id: str) -> None:
        """Close a specific context"""
        if self._closed or not self._ws or self._ws.closed:
            raise ConnectionError("WebSocket connection is closed")
        self._input_queue.send_nowait(_CloseContext(context_id))
    
    async def _send_loop(self) -> None:
        """Send loop - processes messages from input queue"""
        try:
            while not self._closed:
                try:
                    msg = await self._input_queue.recv()
                except Exception:
                    break
                
                if not self._ws or self._ws.closed:
                    break
                
                if isinstance(msg, _SynthesizeContent):
                    is_new_context = msg.context_id not in self._active_contexts
                    
                    # Skip if not current and new context
                    if not self._is_current and is_new_context:
                        continue
                    
                    # Initialize context
                    if is_new_context:
                        voice_settings_dict = None
                        if self._opts.voice_settings:
                            voice_settings_dict = _strip_nones(
                                dataclasses.asdict(self._opts.voice_settings)
                            )
                        
                        init_pkt = {
                            "text": " ",
                            "context_id": msg.context_id,
                        }
                        if voice_settings_dict:
                            init_pkt["voice_settings"] = voice_settings_dict
                        
                        await self._ws.send_json(init_pkt)
                        self._active_contexts.add(msg.context_id)
                    
                    # Send text
                    pkt: dict[str, Any] = {
                        "text": msg.text,
                        "context_id": msg.context_id,
                    }
                    if msg.flush:
                        pkt["flush"] = True
                    
                    await self._ws.send_json(pkt)
                
                elif isinstance(msg, _CloseContext):
                    if msg.context_id in self._active_contexts:
                        close_pkt = {
                            "context_id": msg.context_id,
                            "close_context": True,
                        }
                        await self._ws.send_json(close_pkt)
        
        except Exception as e:
            logger.bind(tag=__name__).error(f"Send loop error: {e}")
        finally:
            if not self._closed:
                await self.aclose()
    
    async def _recv_loop(self) -> None:
        """Receive loop - processes messages from WebSocket"""
        try:
            while not self._closed and self._ws and not self._ws.closed:
                msg = await self._ws.receive()
                
                if msg.type in (
                    aiohttp.WSMsgType.CLOSED,
                    aiohttp.WSMsgType.CLOSE,
                    aiohttp.WSMsgType.CLOSING,
                ):
                    raise APIStatusError(
                        "ElevenLabs connection closed unexpectedly", request_id=""
                    )
                
                if msg.type != aiohttp.WSMsgType.TEXT:
                    logger.bind(tag=__name__).warning(f"Unexpected message type: {msg.type}")
                    continue
                
                data = json.loads(msg.data)
                context_id = data.get("contextId")
                
                if not context_id or context_id not in self._context_data:
                    continue
                
                ctx = self._context_data[context_id]
                
                # Check for errors
                if error := data.get("error"):
                    logger.bind(tag=__name__).error(f"ElevenLabs error: {error}")
                    if not ctx.waiter.done():
                        ctx.waiter.set_exception(RuntimeError(f"ElevenLabs error: {error}"))
                    self._cleanup_context(context_id)
                    continue
                
                # Start segment on first audio
                if audio_b64 := data.get("audio"):
                    # Check if this is the first audio for this context
                    if context_id not in self._active_contexts:
                        ctx.emitter.start_segment(segment_id=context_id)
                        self._active_contexts.add(context_id)
                    
                    audio_bytes = base64.b64decode(audio_b64)
                    ctx.emitter.push(audio_bytes)
                
                # Check if final
                if data.get("isFinal"):
                    if not ctx.waiter.done():
                        ctx.waiter.set_result(None)
                    self._cleanup_context(context_id)
                    
                    if not self._is_current and not self._active_contexts:
                        logger.bind(tag=__name__).debug("No active contexts, shutting down")
                        break
        
        except Exception as e:
            logger.bind(tag=__name__).error(f"Receive loop error: {e}")
            for ctx in self._context_data.values():
                if not ctx.waiter.done():
                    ctx.waiter.set_exception(e)
            self._context_data.clear()
        finally:
            if not self._closed:
                await self.aclose()
    
    def _cleanup_context(self, context_id: str) -> None:
        """Clean up context state"""
        self._context_data.pop(context_id, None)
        self._active_contexts.discard(context_id)
    
    async def aclose(self) -> None:
        """Close the connection and clean up"""
        if self._closed:
            return
        
        self._closed = True
        self._input_queue.close()
        
        # Complete all waiters
        for ctx in self._context_data.values():
            if not ctx.waiter.done():
                ctx.waiter.set_exception(ConnectionError("Connection closed"))
        self._context_data.clear()
        
        # Close WebSocket
        if self._ws:
            await self._ws.close()
        
        # Cancel tasks
        if self._send_task:
            await cancel_and_wait(self._send_task)
        if self._recv_task:
            await cancel_and_wait(self._recv_task)
        
        self._ws = None


def _strip_nones(data: dict[str, Any]) -> dict[str, Any]:
    """Remove None values from dictionary"""
    return {k: v for k, v in data.items() if v is not None}

