from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import queue
from typing import TYPE_CHECKING, AsyncIterator, Callable, Optional, Union
from queue import Queue, Empty
import asyncio
import numpy as np
import time
import opuslib_next

from config.logger import setup_logging
from .dto import VADEvent, VADEventType
from core.providers.asr.dto import ASRMessageType, ASRInputMessage

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()

# Audio constants
SAMPLE_RATE = 16000
CHANNELS = 1
OPUS_FRAME_SAMPLES = 960  # 60ms at 16kHz


class ExpFilter:
    """Exponential filter for smoothing probability values
    
    Smooths noisy VAD probability outputs to reduce false triggers.
    Formula: smoothed = alpha * current + (1-alpha) * previous
    
    Args:
        alpha: Smoothing factor (0-1). Higher = faster response, less smoothing.
    """
    def __init__(self, alpha: float = 0.35):
        self._alpha = alpha
        self._filtered_value: Optional[float] = None

    def apply(self, sample: float) -> float:
        if self._filtered_value is None:
            self._filtered_value = sample
        else:
            self._filtered_value = self._alpha * sample + (1 - self._alpha) * self._filtered_value
        return self._filtered_value

    def reset(self):
        self._filtered_value = None


class VADProviderBase(ABC):
    """Base class for VAD providers
    
    VAD provider loads the model once and creates VADStream instances
    for each connection.
    """

    def __init__(self):
        super().__init__()
    
    @abstractmethod
    def stream(self) -> VADStream: ...


class VADStream(ABC):
    """Base class for VAD stream processing
    
    Each connection should have its own VADStream instance.
    The stream maintains internal state and outputs VADEvent objects.
    """

    class _FlushSentinel:
        pass
    
    def __init__(self, vad: VADProviderBase):
        self._vad = vad
        self._last_activity_time = time.perf_counter()
        self._is_closed = False
        self._input_queue = asyncio.Queue[Union[bytes, VADStream._FlushSentinel]]()
        self._output_queue = asyncio.Queue[VADEvent]()
        
        # Each stream has its own decoder to maintain independent state
        self._decoder = opuslib_next.Decoder(SAMPLE_RATE, CHANNELS)
        
        # This allows VADStream to be instantiated outside of async context
        self._task = None
        # Event callback
        self._event_callback: Optional[Callable[[VADEvent], None]] = None
    
    async def start(self) -> None:
        """Start the VAD processing task
        
        Must be called in an async context (running event loop).
        This is separated from __init__ to allow instantiation in sync context.
        """
        if self._task is not None:
            logger.bind(tag=TAG).warning("VAD stream already started")
            return
        
        self._task = asyncio.create_task(self._run_task())
        logger.bind(tag=TAG).info("VAD stream task started")
    
    @abstractmethod
    async def _run_task(self) -> None:
        """Main processing loop - processes PCM data from input queue
        
        Subclass should implement this to:
        1. await self._input_queue.get() to receive PCM data
        2. Process the PCM data
        3. Call self._emit_event() to output VADEvent
        """
        ...
        
    def push_audio(self, opus_data: bytes) -> None:
        """Push opus audio packet for processing
        
        Decodes opus to PCM and queues for processing.
        
        Args:
            opus_data: Opus encoded audio packet
        """
        if self._is_closed:
            return
        
        try:
            # Decode opus to PCM in base class
            pcm_data = self._decoder.decode(opus_data, OPUS_FRAME_SAMPLES)
            self._input_queue.put_nowait(pcm_data)
        except opuslib_next.OpusError as e:
            logger.bind(tag=TAG).error(f"Opus decode error: {e}")
    
    async def close(self) -> None:
        """Close the VAD stream and cancel running task"""
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                logger.bind(tag=TAG).info("VAD stream task cancelled")
            except Exception as e:
                logger.bind(tag=TAG).error(f"VAD stream task failed: {e}")
        
        self._task = None
        self._is_closed = True
        self._input_queue = None
        self._output_queue = None

    async def process_events(
        self, 
        conn: "ConnectionHandler",
        asr_input_queue: Queue[ASRInputMessage],
        interrupt_callback: Optional[Callable[["ConnectionHandler"], asyncio.coroutine]] = None,
    ) -> None:
        """Process VAD events from output_queue and send to ASR input queue
        
        This method continuously reads VAD events from output_queue and:
        1. START_OF_SPEECH: Update conn state, send FIRST message, trigger interrupt if needed
        2. INFERENCE_DONE: Send MIDDLE message if speaking
        3. END_OF_SPEECH: Send LAST message, update conn state
        
        Args:
            conn: Connection handler with client state
            asr_input_queue: Queue to send ASR input messages
            interrupt_callback: Optional async callback for interrupt handling
        """
        logger.bind(tag=TAG).info("VAD event processor started")
        
        while not self._is_closed:
            try:
                # Wait for VAD event (sync queue with timeout)
                event = await self._output_queue.get()
                
                current_time_ms = time.time() * 1000
                
                if event.type == VADEventType.START_OF_SPEECH:
                    await self._handle_speech_start(
                        conn, event, asr_input_queue, 
                        current_time_ms, interrupt_callback
                    )
                    
                elif event.type == VADEventType.INFERENCE_DONE:
                    # Skip MIDDLE messages for non-streaming ASR
                    # LAST message already contains complete audio segment
                    # TODO: For streaming ASR, implement incremental audio handling
                    pass
                    
                elif event.type == VADEventType.END_OF_SPEECH:
                    await self._handle_speech_end(
                        conn, event, asr_input_queue, current_time_ms
                    )
                    
            except asyncio.CancelledError:
                logger.bind(tag=TAG).info("VAD event processor cancelled")
                break
            except Exception as e:
                logger.bind(tag=TAG).error(f"Error processing VAD event: {e}")
                continue
        
        logger.bind(tag=TAG).info("VAD event processor stopped")

    async def _handle_speech_start(
        self,
        conn: "ConnectionHandler",
        event: VADEvent,
        asr_input_queue: Queue[ASRInputMessage],
        current_time_ms: float,
        interrupt_callback: Optional[Callable[["ConnectionHandler"], asyncio.coroutine]] = None,
    ) -> None:
        """Handle START_OF_SPEECH event
        
        1. Update conn state (client_have_voice = True)
        2. Send FIRST message to ASR queue
        3. Check if interrupt is needed (client_is_speaking)
        """
        logger.bind(tag=TAG).debug(
            f"Speech start detected: prob={event.probability:.2f}, "
            f"duration={event.speech_duration:.2f}s"
        )
        
        # Update connection state - voice started
        conn.client_have_voice = True
        
        # Record latency tracking timestamp
        conn._latency_voice_start_time = current_time_ms
        
        # Send FIRST message to ASR queue
        asr_message = ASRInputMessage(
            message_type=ASRMessageType.FIRST,
            audio_data=event.audio_data,
            speech_duration=event.speech_duration,
            probability=event.probability,
            timestamp_ms=current_time_ms,
        )
        asr_input_queue.put_nowait(asr_message)
        
        logger.bind(tag=TAG).info(
            f"ASR FIRST message sent: audio={asr_message.audio_duration_ms:.0f}ms"
        )
        
        # Check if interrupt is needed
        # When TTS is speaking and user starts talking, trigger interrupt
        if conn.client_is_speaking and conn.client_listen_mode != "manual":
            logger.bind(tag=TAG).info(
                "User started speaking while Agent is speaking, triggering interrupt"
            )
            if interrupt_callback:
                try:
                    await interrupt_callback(conn)
                except Exception as e:
                    logger.bind(tag=TAG).error(f"Interrupt callback failed: {e}")

    async def _handle_inference_done(
        self,
        conn: "ConnectionHandler",
        event: VADEvent,
        asr_input_queue: Queue[ASRInputMessage],
        current_time_ms: float,
    ) -> None:
        """Handle INFERENCE_DONE event
        
        Only send MIDDLE message if speech is ongoing (conn.client_have_voice)
        """
        # Only send audio if client is speaking
        if not conn.client_have_voice or not event.speaking:
            return
        
        # Send MIDDLE message to ASR queue
        asr_message = ASRInputMessage(
            message_type=ASRMessageType.MIDDLE,
            audio_data=event.audio_data,
            speech_duration=event.speech_duration,
            probability=event.probability,
            timestamp_ms=current_time_ms,
        )
        asr_input_queue.put_nowait(asr_message)
        
        logger.bind(tag=TAG).debug(
            f"ASR MIDDLE message sent: prob={event.probability:.2f}, "
            f"speech={event.speech_duration:.2f}s"
        )

    async def _handle_speech_end(
        self,
        conn: "ConnectionHandler",
        event: VADEvent,
        asr_input_queue: Queue[ASRInputMessage],
        current_time_ms: float,
    ) -> None:
        """Handle END_OF_SPEECH event
        
        1. Send LAST message to ASR queue
        2. Update conn state (client_voice_stop = True)
        """
        logger.bind(tag=TAG).debug(
            f"Speech end detected: duration={event.speech_duration:.2f}s, "
            f"silence={event.silence_duration:.2f}s"
        )
        
        # Record latency tracking timestamp for voice end
        conn._latency_voice_end_time = current_time_ms
        
        # Calculate voice duration for latency tracking
        if hasattr(conn, '_latency_voice_start_time'):
            voice_duration_ms = current_time_ms - conn._latency_voice_start_time
            logger.bind(tag=TAG).info(
                f"🎤 [Latency] Voice segment: {voice_duration_ms:.0f}ms"
            )
        
        # Send LAST message to ASR queue
        asr_message = ASRInputMessage(
            message_type=ASRMessageType.LAST,
            audio_data=event.audio_data,
            speech_duration=event.speech_duration,
            probability=event.probability,
            timestamp_ms=current_time_ms,
        )
        asr_input_queue.put_nowait(asr_message)
        
        logger.bind(tag=TAG).info(
            f"ASR LAST message sent: total_speech={event.speech_duration:.2f}s, "
            f"audio={asr_message.audio_duration_ms:.0f}ms"
        )
        
        # Update connection state - voice stopped
        conn.client_voice_stop = True
        conn.client_have_voice = False





