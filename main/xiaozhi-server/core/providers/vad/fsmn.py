import asyncio
import time
import numpy as np
from dataclasses import dataclass
from funasr import AutoModel

from config.logger import setup_logging
from .base import VADProviderBase, VADStream
from .dto import VADEvent, VADEventType


TAG = __name__
logger = setup_logging()


@dataclass
class FsmnVADOptions:
    """FSMN VAD specific options"""
    prefix_padding_duration: float = 0.3    # 300ms prefix padding
    sample_rate: int = 16000                # 16kHz
    chunk_size_ms: int = 100                # FSMN chunk size


class VADProvider(VADProviderBase):
    """FSMN VAD provider using FunASR"""
    
    def __init__(self, config: dict):
        super().__init__()
        
        model_name = config.get("model", "fsmn-vad")
        model_revision = config.get("model_revision", "v2.0.4")
        
        self._model = AutoModel(model=model_name, model_revision=model_revision)
        
        # Parse config
        chunk_size_ms = int(config.get("chunk_size_ms", "100"))
        self._opts = FsmnVADOptions(
            prefix_padding_duration=float(config.get("prefix_padding_duration", "0.3")),
            sample_rate=16000,
            chunk_size_ms=chunk_size_ms,
        )
        

    
    def stream(self) -> VADStream:
        """Create a new VAD stream"""
        return FsmnVADStream(self, self._model, self._opts)


class FsmnVADStream(VADStream):
    """FSMN VAD stream implementation using FunASR
    
    FSMN VAD outputs events:
    - [start, -1]  -> speech start
    - [-1, end]    -> speech end
    - [start, end] -> complete short segment (ignored)
    - []           -> no event, keep current state
    """
    
    def __init__(self, vad: VADProvider, model, opts: FsmnVADOptions):
        super().__init__(vad)
        self._model = model
        self._opts = opts
        
        # FSMN chunk size
        self._chunk_samples = int(opts.chunk_size_ms * opts.sample_rate / 1000)
        self._chunk_bytes = self._chunk_samples * 2  # int16
        self._chunk_duration = opts.chunk_size_ms / 1000  # seconds
        
        # Speech buffer for prefix padding (in bytes, not samples)
        self._prefix_padding_bytes = int(opts.prefix_padding_duration * opts.sample_rate) * 2
        # Pre-allocate max speech buffer (60s + prefix padding)
        max_speech_bytes = 60 * opts.sample_rate * 2 + self._prefix_padding_bytes
        self._speech_buffer = bytearray(max_speech_bytes)
        self._speech_buffer_max_reached = False
    
    def _get_speech_audio(self, end_index: int) -> bytes:
        """Get the accumulated speech audio data"""
        return bytes(self._speech_buffer[:end_index])
    
    async def _run_task(self) -> None:
        """Main processing loop - receives PCM data from base class"""
        
        # Local state variables
        speech_buffer_index: int = 0
        speaking = False
        speech_duration = 0.0
        silence_duration = 0.0
        speech_start_ms = 0
        
        # Two buffers: one for inference, one for copying to speech buffer
        input_audios: bytearray = bytearray()
        inference_audios: bytearray = bytearray()
        
        # FSMN cache for streaming (reset on speech end)
        fsmn_cache = {}
        
        while not self._is_closed:
            try:
                pcm_data = await self._input_queue.get()
                if isinstance(pcm_data, VADStream._FlushSentinel):
                    continue
                
                # Accumulate PCM data to both buffers
                input_audios.extend(pcm_data)
                inference_audios.extend(pcm_data)
                
                # Process complete chunks
                while len(inference_audios) >= self._chunk_bytes:
                    inference_start = time.perf_counter()
                    
                    # Extract chunk, convert int16 to float32
                    chunk_int16 = np.frombuffer(
                        inference_audios[:self._chunk_bytes], dtype=np.int16
                    )
                    chunk_float32 = chunk_int16.astype(np.float32) / 32768.0
                    
                    # Run FSMN inference
                    res = self._model.generate(
                        input=chunk_float32,
                        cache=fsmn_cache,
                        is_final=False,
                        chunk_size=self._opts.chunk_size_ms
                    )
                    
                    inference_duration = time.perf_counter() - inference_start
                    
                    # Copy chunk to speech buffer
                    available_space = len(self._speech_buffer) - speech_buffer_index
                    to_copy = min(available_space, self._chunk_bytes)
                    
                    if to_copy > 0:
                        self._speech_buffer[speech_buffer_index:speech_buffer_index + to_copy] = input_audios[:to_copy]
                        speech_buffer_index += to_copy
                    elif not self._speech_buffer_max_reached:
                        self._speech_buffer_max_reached = True
                        logger.bind(tag=TAG).warning("Speech buffer max reached, dropping further audio")
                    
                    def _reset_write_cursor() -> None:
                        nonlocal speech_buffer_index
                        if speech_buffer_index <= self._prefix_padding_bytes:
                            return
                        
                        # Keep last prefix_padding worth of audio
                        padding_data = self._speech_buffer[
                            speech_buffer_index - self._prefix_padding_bytes : speech_buffer_index
                        ]
                        
                        self._speech_buffer_max_reached = False
                        self._speech_buffer[: self._prefix_padding_bytes] = padding_data
                        speech_buffer_index = self._prefix_padding_bytes
                    
                    def _copy_speech_buffer() -> bytes:
                        return bytes(self._speech_buffer[:speech_buffer_index])
                    
                    # Parse FSMN result
                    # res format: [{"key": "xxx", "value": [[start_ms, end_ms], ...]}]
                    if res and len(res) > 0 and res[0].get("value"):
                        seg = res[0]["value"][0]  # Take first segment
                        seg_start, seg_end = seg[0], seg[1]
                        
                        if seg_start > 0 and seg_end == -1:
                            # Speech start event
                            if not speaking:
                                speaking = True
                                speech_start_ms = seg_start
                                silence_duration = 0.0
                                
                                # Emit START_OF_SPEECH
                                self._output_queue.put_nowait(VADEvent(
                                    type=VADEventType.START_OF_SPEECH,
                                    speech_duration=0.0,
                                    silence_duration=0.0,
                                    speaking=True,
                                    audio_data=_copy_speech_buffer(),
                                    inference_duration=inference_duration,
                                ))
                                logger.bind(tag=TAG).info(
                                    f"🎤 FSMN VAD START_OF_SPEECH @{seg_start}ms"
                                )
                                
                        elif seg_start == -1 and seg_end > 0:
                            # Speech end event
                            if speaking:
                                speaking = False
                                speech_duration_ms = seg_end - speech_start_ms
                                speech_duration = speech_duration_ms / 1000
                                
                                # Emit END_OF_SPEECH
                                self._output_queue.put_nowait(VADEvent(
                                    type=VADEventType.END_OF_SPEECH,
                                    speech_duration=speech_duration,
                                    silence_duration=silence_duration,
                                    speaking=False,
                                    audio_data=_copy_speech_buffer(),
                                    inference_duration=inference_duration,
                                ))
                                logger.bind(tag=TAG).info(
                                    f"🔇 FSMN VAD END_OF_SPEECH @{seg_end}ms | "
                                    f"duration={speech_duration:.2f}s"
                                )
                                
                                # Reset for next utterance
                                speech_duration = 0.0
                                fsmn_cache = {}
                                _reset_write_cursor()
                                
                        elif seg_start > 0 and seg_end > 0:
                            # Complete short segment - ignore
                            logger.bind(tag=TAG).debug(
                                f"FSMN: short segment [{seg_start}, {seg_end}]ms (ignored)"
                            )
                    
                    # Update durations based on current state
                    if speaking:
                        speech_duration += self._chunk_duration
                    else:
                        silence_duration += self._chunk_duration
                        _reset_write_cursor()
                    
                    # Always emit INFERENCE_DONE
                    self._output_queue.put_nowait(VADEvent(
                        type=VADEventType.INFERENCE_DONE,
                        speech_duration=speech_duration,
                        silence_duration=silence_duration,
                        speaking=speaking,
                        audio_data=_copy_speech_buffer(),
                        inference_duration=inference_duration,
                    ))
                    
                    # Remove processed data from buffers
                    del inference_audios[:self._chunk_bytes]
                    del input_audios[:to_copy]
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.bind(tag=TAG).error(f"Error in VAD task: {e}")
    
    def reset(self):
        """Reset stream state for new utterance"""
        # Note: Local variables in _run_task are reset by restarting the task
        self._speech_buffer_max_reached = False
