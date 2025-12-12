from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class VADEventType(Enum):
    """VAD event types"""
    START_OF_SPEECH = "start_of_speech"    # Speech started (after min_speech_duration)
    INFERENCE_DONE = "inference_done"       # Inference completed (every frame)
    END_OF_SPEECH = "end_of_speech"         # Speech ended (after min_silence_duration)


@dataclass
class VADEvent:
    """VAD event data structure
    
    Attributes:
        type: Event type (START_OF_SPEECH, INFERENCE_DONE, END_OF_SPEECH)
        probability: Speech probability for current frame (0.0-1.0)
        speech_duration: Accumulated speech duration in seconds
        silence_duration: Accumulated silence duration in seconds
        speaking: Whether currently speaking
        audio_data: Audio data associated with this event (bytes, PCM 16-bit)
            - START_OF_SPEECH: prefix padding + speech start
            - INFERENCE_DONE: current inference window
            - END_OF_SPEECH: complete speech segment with padding
        inference_duration: Time taken for inference in seconds
    """
    type: VADEventType
    probability: float = 0.0                # speech probability (0.0-1.0)
    speech_duration: float = 0.0            # accumulated speech duration (seconds)
    silence_duration: float = 0.0           # accumulated silence duration (seconds)
    speaking: bool = False                  # currently speaking
    audio_data: bytes = field(default_factory=bytes)  # PCM audio data
    inference_duration: float = 0.0         # inference time (seconds)
    
    def __repr__(self) -> str:
        audio_len_ms = len(self.audio_data) / 32 if self.audio_data else 0  # 16kHz, 16-bit = 32 bytes/ms
        return (
            f"VADEvent(type={self.type.value}, "
            f"speaking={self.speaking}, "
            f"prob={self.probability:.2f}, "
            f"speech={self.speech_duration:.2f}s, "
            f"silence={self.silence_duration:.2f}s, "
            f"audio={audio_len_ms:.0f}ms)"
        )

