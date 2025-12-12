import asyncio
import time
from numba import byte
import numpy as np
import torch
from dataclasses import dataclass

from config.logger import setup_logging
from .base import VADProviderBase, VADStream, ExpFilter
from .dto import VADEvent, VADEventType


@dataclass
class SileroVADOptions:
    """Silero VAD specific options"""
    min_speech_duration: float = 0.05       # 50ms to confirm speech start
    min_silence_duration: float = 0.40      # 400ms to confirm speech end
    prefix_padding_duration: float = 0.3    # 300ms prefix padding
    activation_threshold: float = 0.5       # probability threshold
    sample_rate: int = 16000                # 16kHz


TAG = __name__
logger = setup_logging()


class VADProvider(VADProviderBase):
    """Silero VAD provider"""
    
    def __init__(self, config: dict):
        super().__init__()
        # Load Silero model
        self._model, _ = torch.hub.load(
            repo_or_dir=config.get("model_dir", "models/snakers4_silero-vad"),
            source="local",
            model="silero_vad",
            force_reload=False,
        )
        
        # Parse config
        self._opts = SileroVADOptions(
            min_speech_duration=float(config.get("min_speech_duration", "0.05")),
            min_silence_duration=float(config.get("min_silence_duration", "0.40")),
            prefix_padding_duration=float(config.get("prefix_padding_duration", "0.3")),
            activation_threshold=float(config.get("threshold", "0.5")),
            sample_rate=16000,
        )
        
    def stream(self) -> VADStream:
        """Create a new VAD stream"""
        return SileroVADStream(self, self._model, self._opts)


class SileroVADStream(VADStream):
    """Silero VAD stream implementation"""
    
    # Silero requires 512 samples per inference (32ms at 16kHz)
    WINDOW_SIZE_SAMPLES = 512
    WINDOW_SIZE_BYTES = WINDOW_SIZE_SAMPLES * 2  # int16
    WINDOW_DURATION = WINDOW_SIZE_SAMPLES / 16000  # seconds
    SLOW_INFERENCE_THRESHOLD = 0.2  # seconds
    
    def __init__(self, vad: VADProvider, model, opts: SileroVADOptions):
        super().__init__(vad)
        self._model = model
        self._opts = opts
        self._exp_filter = ExpFilter(alpha=0.35)
        
        # Speech buffer for prefix padding (in bytes, not samples)
        self._prefix_padding_bytes = int(opts.prefix_padding_duration * opts.sample_rate) * 2
        # Pre-allocate max speech buffer (60s + prefix padding)
        max_speech_bytes = 60 * opts.sample_rate * 2 + self._prefix_padding_bytes
        self._speech_buffer = bytearray(max_speech_bytes)
        self._speech_buffer_max_reached = False
    
    async def _run_task(self) -> None:
        """Main processing loop - receives PCM data from base class"""
        
        inference_data = np.empty(self.WINDOW_SIZE_SAMPLES, dtype=np.float32)
        speech_buffer_index: int = 0
        
        pub_speaking = False
        pub_speech_duration = 0.0
        pub_silence_duration = 0.0
        
        speech_threshold_duration = 0.0
        silence_threshold_duration = 0.0

        extra_inference_time = 0.0
        
        input_audios: bytearray = bytearray()
        inference_audios: bytearray = bytearray()
        
        while not self._is_closed:
            try:
                pcm_data = await self._input_queue.get()
                if isinstance(pcm_data, VADStream._FlushSentinel):
                    continue
                                
                input_audios.extend(pcm_data)
                inference_audios.extend(pcm_data)
                
                # Process complete windows
                while len(inference_audios) >= self.WINDOW_SIZE_BYTES:
                    inference_start = time.perf_counter()
                    
                    # Extract window, convert int16 to float32
                    window_int16 = np.frombuffer(
                        inference_audios[:self.WINDOW_SIZE_BYTES], dtype=np.int16
                    )
                    np.divide(window_int16, 32768.0, out=inference_data)
                    
                    # Convert to tensor and run inference
                    audio_tensor = torch.from_numpy(inference_data)
                    with torch.no_grad():
                        prob = self._model(audio_tensor, self._opts.sample_rate).item()
                    
                    # Apply exponential smoothing
                    prob = self._exp_filter.apply(prob)
                    
                    # Copy inference window to speech buffer
                    available_space = len(self._speech_buffer) - speech_buffer_index
                    to_copy = min(available_space, self.WINDOW_SIZE_BYTES)
                    
                    if to_copy > 0:
                        self._speech_buffer[speech_buffer_index:speech_buffer_index + to_copy] = input_audios[:to_copy]
                        speech_buffer_index += to_copy
                    elif not self._speech_buffer_max_reached:
                        self._speech_buffer_max_reached = True
                        logger.bind(tag=TAG).warning("Speech buffer max reached, dropping further audio")
                    
                    # inference time
                    inference_duration = time.perf_counter() - inference_start
                    extra_inference_time = max(
                        0.0,
                        extra_inference_time + inference_duration - self.WINDOW_DURATION,
                    )

                    if inference_duration > self.SLOW_INFERENCE_THRESHOLD:
                        logger.bind(tag=TAG).warning(
                            "inference is slower than realtime",
                            extra={"delay": extra_inference_time},
                        )
                    
                    def _reset_write_cursor() -> None:
                        nonlocal speech_buffer_index
                        assert self._speech_buffer is not None
                        if speech_buffer_index <= self._prefix_padding_bytes:
                            return
                        
                        # Keep last prefix_padding worth of audio
                        padding_data = self._speech_buffer[
                            speech_buffer_index - self._prefix_padding_bytes : speech_buffer_index
                        ]

                        self._speech_buffer_max_reached = False
                        self._speech_buffer[: self._prefix_padding_bytes] = padding_data
                        speech_buffer_index = self._prefix_padding_bytes

                    # copy the data from speech_buffer
                    def _copy_speech_buffer() -> bytes:
                        # copy the data from speech_buffer
                        assert self._speech_buffer is not None
                        return bytes(self._speech_buffer[:speech_buffer_index])

                    # Update durations
                    if pub_speaking:
                        pub_speech_duration += self.WINDOW_DURATION
                    else:
                        pub_silence_duration += self.WINDOW_DURATION
                    
                    # Emit INFERENCE_DONE
                    self._output_queue.put_nowait(VADEvent(
                        type=VADEventType.INFERENCE_DONE,
                        probability=prob,
                        speech_duration=pub_speech_duration,
                        silence_duration=pub_silence_duration,
                        speaking=pub_speaking,
                        audio_data=input_audios[:to_copy],
                        inference_duration=inference_duration,
                    ))
                    
                    # State machine logic
                    if prob >= self._opts.activation_threshold:
                        speech_threshold_duration += self.WINDOW_DURATION
                        silence_threshold_duration = 0.0
                        
                        if not pub_speaking:
                            if speech_threshold_duration >= self._opts.min_speech_duration:
                                pub_speaking = True
                                pub_silence_duration = 0.0
                                pub_speech_duration = speech_threshold_duration
                                
                                # Emit START_OF_SPEECH
                                self._output_queue.put_nowait(VADEvent(
                                    type=VADEventType.START_OF_SPEECH,
                                    probability=prob,
                                    speech_duration=pub_speech_duration,
                                    silence_duration=0.0,
                                    speaking=True,
                                    audio_data=_copy_speech_buffer(),
                                    inference_duration=inference_duration,
                                ))
                    else:
                        silence_threshold_duration += self.WINDOW_DURATION
                        speech_threshold_duration = 0.0
                        
                        if not pub_speaking:
                            _reset_write_cursor()
                        
                        if pub_speaking and silence_threshold_duration >= self._opts.min_silence_duration:
                            pub_speaking = False
                            pub_silence_duration = silence_threshold_duration
                            
                            # Emit END_OF_SPEECH
                            self._output_queue.put_nowait(VADEvent(
                                type=VADEventType.END_OF_SPEECH,
                                probability=prob,
                                speech_duration=pub_speech_duration,
                                silence_duration=pub_silence_duration,
                                speaking=False,
                                audio_data=_copy_speech_buffer(),
                                inference_duration=inference_duration,
                            ))
                            
                            pub_speech_duration = 0.0
                            _reset_write_cursor()
                    
                    # Remove processed data from buffers
                    del inference_audios[:self.WINDOW_SIZE_BYTES]
                    del input_audios[:to_copy]
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.bind(tag=TAG).error(f"Error in VAD task: {e}")
    
    def reset(self):
        """Reset stream state for new utterance"""
        self._exp_filter.reset()
