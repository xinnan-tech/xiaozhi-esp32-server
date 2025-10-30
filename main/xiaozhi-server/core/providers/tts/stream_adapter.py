"""
Stream Adapter - Wrap non-streaming TTS to provide streaming interface

This module provides StreamAdapter, which wraps a non-streaming TTS provider
(that only supports synthesize()) and provides a streaming interface (stream()).

The adapter works by:
1. Accepting incremental text input via push_text()
2. Using a sentence tokenizer to segment text into sentences
3. Calling the wrapped TTS's synthesize() for each sentence
4. Streaming the audio output as it becomes available

This allows any non-streaming TTS to be used in streaming contexts.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from config.logger import setup_logging
from core.tokenize import SentenceTokenizer, blingfire
from core.tokenize import basic

# 如果 blingfire 不可用，使用 basic 作为回退
if blingfire is None:
    _default_tokenizer_class = basic.SentenceTokenizer
else:
    _default_tokenizer_class = blingfire.SentenceTokenizer
from core.utils.aio import Chan, cancel_and_wait
from core.utils.short_uuid import shortuuid

from .base import SynthesizedAudio, TTS, SynthesizeStream, TTSCapabilities

if TYPE_CHECKING:
    from .emitter import AudioEmitter
    from .pacer import SentenceStreamPacer

logger = setup_logging()


class StreamAdapter(TTS):
    """
    Wrap a non-streaming TTS to provide streaming interface.
    
    This adapter enables any TTS that supports synthesize() to be used
    with the streaming API. It handles:
    - Text tokenization into sentences
    - Sequential synthesis of each sentence
    - Optional pacing to optimize cost/quality
    
    Example:
        # Wrap a non-streaming TTS
        base_tts = SomeTTS(...)
        streaming_tts = StreamAdapter(
            tts=base_tts,
            sentence_tokenizer=_default_tokenizer_class(),
            text_pacing=True  # Enable smart pacing
        )
        
        # Now use it as a streaming TTS
        stream = streaming_tts.stream()
        stream.push_text("Hello ")
        stream.push_text("world!")
        stream.end_input()
        
        async for audio in stream:
            # Process audio frames
            pass
    """
    
    def __init__(
        self,
        *,
        tts: TTS,
        sentence_tokenizer: SentenceTokenizer | None = None,
        text_pacing: bool | SentenceStreamPacer = False,
    ) -> None:
        """
        Initialize StreamAdapter.
        
        Args:
            tts: The non-streaming TTS to wrap
            sentence_tokenizer: Tokenizer to segment text into sentences.
                               Defaults to basic.SentenceTokenizer() (or blingfire if available)
            text_pacing: Smart pacing configuration:
                        - True: Use default SentenceStreamPacer
                        - SentenceStreamPacer instance: Use custom pacer
                        - False: No pacing (synthesize immediately)
        """
        super().__init__(
            capabilities=TTSCapabilities(streaming=True),
            sample_rate=tts.sample_rate,
            num_channels=tts.num_channels,
        )
        self._wrapped_tts = tts
        self._sentence_tokenizer = (
            sentence_tokenizer if sentence_tokenizer else _default_tokenizer_class()
        )
        
        self._stream_pacer: SentenceStreamPacer | None = None
        if text_pacing is True:
            from .pacer import SentenceStreamPacer
            self._stream_pacer = SentenceStreamPacer()
        elif text_pacing is not False:
            # Assume it's a SentenceStreamPacer instance
            self._stream_pacer = text_pacing
    
    @property
    def model(self) -> str:
        """Get the model from wrapped TTS"""
        return self._wrapped_tts.model
    
    @property
    def provider(self) -> str:
        """Get the provider from wrapped TTS"""
        return self._wrapped_tts.provider
    
    def synthesize(self, text: str) -> 'ChunkedStream':
        """
        Synthesize using the wrapped TTS.
        
        Args:
            text: Text to synthesize
        
        Returns:
            ChunkedStream from the wrapped TTS
        """
        return self._wrapped_tts.synthesize(text)
    
    def stream(self) -> StreamAdapterWrapper:
        """
        Create a streaming synthesis session.
        
        Returns:
            StreamAdapterWrapper: Streaming synthesis session
        """
        return StreamAdapterWrapper(tts=self)
    
    def prewarm(self) -> None:
        """Pre-warm the wrapped TTS"""
        self._wrapped_tts.prewarm()
    
    async def aclose(self) -> None:
        """Close the wrapped TTS"""
        await self._wrapped_tts.aclose()


class StreamAdapterWrapper(SynthesizeStream):
    """
    Streaming wrapper that synthesizes sentences sequentially.
    
    This class orchestrates:
    1. Reading incremental text from input channel
    2. Tokenizing text into sentences
    3. Optionally pacing sentence dispatch based on audio buffer
    4. Calling wrapped TTS for each sentence
    5. Streaming audio output
    """
    
    def __init__(self, *, tts: StreamAdapter) -> None:
        """
        Initialize StreamAdapterWrapper.
        
        Args:
            tts: The StreamAdapter instance
        """
        super().__init__(tts=tts)
        self._tts: StreamAdapter = tts
    
    async def _run(self, output_emitter: AudioEmitter) -> None:
        """
        Main streaming synthesis logic.
        
        This method:
        1. Initializes the output emitter
        2. Creates sentence tokenizer stream (and optional pacer)
        3. Spawns two parallel tasks:
           - _forward_input: Reads from input_ch → tokenizer
           - _synthesize: Reads tokenized sentences → TTS → emitter
        
        Args:
            output_emitter: AudioEmitter to push synthesized audio to
        """
        # 1. Initialize output emitter
        request_id = shortuuid()
        output_emitter.initialize(
            request_id=request_id,
            sample_rate=self._tts.sample_rate,
            num_channels=self._tts.num_channels,
            stream=True,
        )
        
        # 2. Create sentence tokenizer stream
        sent_stream = self._tts._sentence_tokenizer.stream()
        
        # 3. Optionally wrap with pacer
        if self._tts._stream_pacer:
            sent_stream = self._tts._stream_pacer.wrap(
                sent_stream=sent_stream,
                audio_emitter=output_emitter,
            )
        
        # 4. Start segment
        segment_id = shortuuid()
        output_emitter.start_segment(segment_id=segment_id)
        
        # 5. Define parallel tasks
        async def _forward_input() -> None:
            """Forward text from input channel to tokenizer"""
            try:
                async for data in self._input_ch:
                    if isinstance(data, self._FlushSentinel):
                        sent_stream.flush()
                        continue
                    
                    sent_stream.push_text(data)
            finally:
                sent_stream.end_input()
        
        async def _synthesize() -> None:
            """
            Synthesize each sentence and push audio to emitter.
            
            For each tokenized sentence:
            1. Call wrapped_tts.synthesize(sentence)
            2. Stream audio frames from the synthesis
            3. Push each frame's audio data to output_emitter
            4. Flush after each sentence
            """
            try:
                async for sentence_ev in sent_stream:
                    # Skip empty sentences
                    text = sentence_ev.token.strip()
                    if not text:
                        continue
                    
                    # Synthesize this sentence using wrapped TTS
                    async with self._tts._wrapped_tts.synthesize(text) as tts_stream:
                        async for audio in tts_stream:
                            # Push audio data to emitter
                            # Note: audio.frame.data is memoryview, convert to bytes
                            audio_bytes = bytes(audio.frame.data)
                            output_emitter.push(audio_bytes)
                        
                        # Flush after each sentence
                        output_emitter.flush()
            except Exception as e:
                logger.bind(tag=__name__).error(f"Synthesis error: {e}")
                raise
        
        # 6. Run both tasks in parallel
        tasks = [
            asyncio.create_task(_forward_input(), name="forward_input"),
            asyncio.create_task(_synthesize(), name="synthesize"),
        ]
        
        try:
            await asyncio.gather(*tasks)
        finally:
            await sent_stream.aclose()
            await cancel_and_wait(*tasks)

