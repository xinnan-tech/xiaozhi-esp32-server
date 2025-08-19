"""Voice Activity Detection (VAD) analyzer base classes and utilities.

This module provides the abstract base class for VAD analyzers and associated
data structures for voice activity detection in audio streams.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional
from pydantic import BaseModel
import numpy as np
from config.logger import setup_logging

logger = setup_logging()

# Default VAD parameters
VAD_CONFIDENCE = 0.5
VAD_START_SECS = 0.2
VAD_STOP_SECS = 0.8
VAD_MIN_VOLUME = 0.001  # Very low default - essentially confidence-only detection


class VADState(Enum):
    """Voice Activity Detection states.
    
    States:
        QUIET: No voice activity detected
        STARTING: Voice activity beginning, transitioning from quiet
        SPEAKING: Active voice detected and confirmed
        STOPPING: Voice activity ending, transitioning to quiet
    """
    QUIET = 1
    STARTING = 2
    SPEAKING = 3
    STOPPING = 4


class VADParams(BaseModel):
    """Configuration parameters for Voice Activity Detection.
    
    Attributes:
        confidence: Minimum confidence threshold for voice detection (0.0-1.0)
        start_secs: Duration to wait before confirming voice start
        stop_secs: Duration to wait before confirming voice stop
        min_volume: Minimum audio volume threshold for voice detection
    """
    confidence: float = VAD_CONFIDENCE
    start_secs: float = VAD_START_SECS
    stop_secs: float = VAD_STOP_SECS
    min_volume: float = VAD_MIN_VOLUME


def calculate_audio_volume(audio: bytes, sample_rate: int) -> float:
    """Calculate RMS volume of audio data.
    
    Args:
        audio: Raw audio bytes
        sample_rate: Audio sample rate in Hz
        
    Returns:
        RMS volume normalized to 0.0-1.0 range
    """
    audio_int16 = np.frombuffer(audio, dtype=np.int16)
    audio_float32 = audio_int16.astype(np.float32) / 32768.0
    rms = np.sqrt(np.mean(audio_float32 ** 2))
    return float(rms)


def exp_smoothing(current: float, previous: float, factor: float) -> float:
    """Apply exponential smoothing to a value.
    
    Args:
        current: Current value
        previous: Previous smoothed value
        factor: Smoothing factor (0.0-1.0)
        
    Returns:
        Smoothed value
    """
    return factor * current + (1 - factor) * previous


class VADAnalyzer(ABC):
    """Abstract base class for Voice Activity Detection analyzers.
    
    Provides the framework for implementing VAD analysis with configurable
    parameters, state management, and audio processing capabilities.
    """
    
    def __init__(self, *, sample_rate: Optional[int] = None, params: Optional[VADParams] = None):
        """Initialize the VAD analyzer.
        
        Args:
            sample_rate: Audio sample rate in Hz. If None, will be set later
            params: VAD parameters for detection configuration
        """
        self._init_sample_rate = sample_rate
        self._sample_rate = 0
        self._params = params or VADParams()
        self._num_channels = 1
        
        self._vad_buffer = b""
        
        # Volume exponential smoothing
        self._smoothing_factor = 0.2
        self._prev_volume = 0
        
        # Initialize VAD state variables
        self._vad_state = VADState.QUIET
        self._vad_starting_count = 0
        self._vad_stopping_count = 0
        self._vad_frames = 0
        self._vad_frames_num_bytes = 0
        self._vad_start_frames = 0
        self._vad_stop_frames = 0
        
    @property
    def sample_rate(self) -> int:
        """Get the current sample rate."""
        return self._sample_rate
        
    @property
    def num_channels(self) -> int:
        """Get the number of audio channels."""
        return self._num_channels
        
    @property
    def params(self) -> VADParams:
        """Get the current VAD parameters."""
        return self._params
        
    @abstractmethod
    def num_frames_required(self) -> int:
        """Get the number of audio frames required for analysis."""
        pass
        
    @abstractmethod
    def voice_confidence(self, buffer: bytes) -> float:
        """Calculate voice activity confidence for the given audio buffer.
        
        Args:
            buffer: Audio buffer to analyze
            
        Returns:
            Voice confidence score between 0.0 and 1.0
        """
        pass
        
    def set_sample_rate(self, sample_rate: int):
        """Set the sample rate for audio processing.
        
        Args:
            sample_rate: Audio sample rate in Hz
        """
        self._sample_rate = self._init_sample_rate or sample_rate
        self.set_params(self._params)
        
    def set_params(self, params: VADParams):
        """Set VAD parameters and recalculate internal values.
        
        Args:
            params: VAD parameters for detection configuration
        """
        logger.debug(f"Setting VAD params to: {params}")
        self._params = params
        self._vad_frames = self.num_frames_required()
        self._vad_frames_num_bytes = self._vad_frames * self._num_channels * 2
        
        vad_frames_per_sec = self._vad_frames / self.sample_rate if self.sample_rate > 0 else 1
        
        self._vad_start_frames = round(self._params.start_secs / vad_frames_per_sec)
        self._vad_stop_frames = round(self._params.stop_secs / vad_frames_per_sec)
        self._vad_starting_count = 0
        self._vad_stopping_count = 0
        self._vad_state: VADState = VADState.QUIET
        
    def _get_smoothed_volume(self, audio: bytes) -> float:
        """Calculate smoothed audio volume using exponential smoothing."""
        volume = calculate_audio_volume(audio, self.sample_rate)
        return exp_smoothing(volume, self._prev_volume, self._smoothing_factor)
        
    def reset(self):
        """Reset the VAD analyzer to initial state."""
        self._vad_buffer = b""
        self._vad_state = VADState.QUIET
        self._vad_starting_count = 0
        self._vad_stopping_count = 0
        self._prev_volume = 0
        
    def analyze_audio(self, buffer: bytes) -> VADState:
        """Analyze audio buffer and return current VAD state.
        
        Processes incoming audio data, maintains internal state, and determines
        voice activity status based on confidence and volume thresholds.
        
        Args:
            buffer: Audio buffer to analyze
            
        Returns:
            Current VAD state after processing the buffer
        """
        self._vad_buffer += buffer
        
        num_required_bytes = self._vad_frames_num_bytes
        if len(self._vad_buffer) < num_required_bytes:
            return self._vad_state
            
        while len(self._vad_buffer) >= num_required_bytes:
            audio_frames = self._vad_buffer[:num_required_bytes]
            self._vad_buffer = self._vad_buffer[num_required_bytes:]
            
            confidence = self.voice_confidence(audio_frames)
            
            volume = self._get_smoothed_volume(audio_frames)
            self._prev_volume = volume
            
            speaking = confidence >= self._params.confidence and volume >= self._params.min_volume
            
            # Debug logging for troubleshooting
            if not hasattr(self, '_debug_log_counter'):
                self._debug_log_counter = 0
            self._debug_log_counter += 1
            
            if self._debug_log_counter % 10 == 0:
                logger.debug(f"VAD analysis: confidence={confidence:.3f} (threshold={self._params.confidence}), "
                           f"volume={volume:.4f} (threshold={self._params.min_volume}), "
                           f"speaking={speaking}")
            
            if speaking:
                if self._vad_state == VADState.QUIET:
                    self._vad_state = VADState.STARTING
                    self._vad_starting_count = 1
                elif self._vad_state == VADState.STARTING:
                    self._vad_starting_count += 1
                elif self._vad_state == VADState.STOPPING:
                    self._vad_state = VADState.SPEAKING
                    self._vad_stopping_count = 0
            else:
                if self._vad_state == VADState.STARTING:
                    self._vad_state = VADState.QUIET
                    self._vad_starting_count = 0
                elif self._vad_state == VADState.SPEAKING:
                    self._vad_state = VADState.STOPPING
                    self._vad_stopping_count = 1
                elif self._vad_state == VADState.STOPPING:
                    self._vad_stopping_count += 1
                    
        if (self._vad_state == VADState.STARTING and 
            self._vad_starting_count >= self._vad_start_frames):
            self._vad_state = VADState.SPEAKING
            self._vad_starting_count = 0
            
        if (self._vad_state == VADState.STOPPING and 
            self._vad_stopping_count >= self._vad_stop_frames):
            self._vad_state = VADState.QUIET
            self._vad_stopping_count = 0
            
        return self._vad_state