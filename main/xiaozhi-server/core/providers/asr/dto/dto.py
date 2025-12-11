from dataclasses import dataclass, field
from enum import Enum
from typing import Union, Optional


class InterfaceType(Enum):
    """ASR interface types"""
    STREAM = "STREAM"          # Streaming interface
    NON_STREAM = "NON_STREAM"  # Non-streaming interface
    LOCAL = "LOCAL"            # Local service


class ASRMessageType(Enum):
    """ASR input message types
    
    Defines the position of audio chunk in a speech segment:
    - FIRST: First chunk of a speech segment (speech start detected)
    - MIDDLE: Middle chunk of a speech segment (during speaking)
    - LAST: Last chunk of a speech segment (speech end detected)
    """
    FIRST = "FIRST"      # Speech started
    MIDDLE = "MIDDLE"    # During speech
    LAST = "LAST"        # Speech ended


@dataclass
class ASRInputMessage:
    """ASR input message data structure
    
    Represents an audio chunk sent to ASR service for transcription.
    
    Attributes:
        message_type: Position of this chunk in the speech segment
        audio_data: PCM audio data (16-bit, 16kHz, mono)
        speech_duration: Accumulated speech duration in seconds (from VAD)
        probability: Speech probability for this chunk (0.0-1.0)
        timestamp_ms: Timestamp when this message was created
    """
    message_type: ASRMessageType
    audio_data: bytes = field(default_factory=bytes)
    speech_duration: float = 0.0
    probability: float = 0.0
    timestamp_ms: float = 0.0
    
    @property
    def is_first(self) -> bool:
        """Check if this is the first message of a speech segment"""
        return self.message_type == ASRMessageType.FIRST
    
    @property
    def is_last(self) -> bool:
        """Check if this is the last message of a speech segment"""
        return self.message_type == ASRMessageType.LAST
    
    @property
    def audio_duration_ms(self) -> float:
        """Calculate audio duration in milliseconds"""
        # 16kHz, 16-bit mono = 32 bytes per ms
        return len(self.audio_data) / 32 if self.audio_data else 0.0
