"""
Silero VAD Stream Unit Tests

This test suite demonstrates how the VAD stream works:

1. VAD Stream Architecture:
   ┌──────────────┐     ┌───────────────┐     ┌──────────────┐
   │ push_audio() │ --> │ _input_queue  │ --> │ _run_task()  │
   │ (opus data)  │     │ (PCM bytes)   │     │ (inference)  │
   └──────────────┘     └───────────────┘     └──────┬───────┘
                                                      │
                                                      v
                                              ┌───────────────┐
                                              │ _output_queue │
                                              │ (VADEvent)    │
                                              └───────────────┘

2. State Machine:
   - IDLE state: Accumulate silence, reset buffer (keep prefix padding)
   - When prob >= threshold for min_speech_duration → emit START_OF_SPEECH
   - SPEAKING state: Accumulate speech audio
   - When prob < threshold for min_silence_duration → emit END_OF_SPEECH

3. Buffer Management:
   - speech_buffer: Pre-allocated 60s + prefix_padding (for complete utterance)
   - prefix_padding: 300ms audio kept before speech start
   - _reset_write_cursor(): Slides buffer to keep only last 300ms
"""

import asyncio
import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import sys
import os


# ============================================================================
# Local copies of VAD types to avoid importing opuslib-dependent modules
# ============================================================================

class VADEventType(Enum):
    """VAD event types"""
    START_OF_SPEECH = "start_of_speech"
    INFERENCE_DONE = "inference_done"
    END_OF_SPEECH = "end_of_speech"


@dataclass
class VADEvent:
    """VAD event data structure"""
    type: VADEventType
    probability: float = 0.0
    speech_duration: float = 0.0
    silence_duration: float = 0.0
    speaking: bool = False
    audio_data: bytes = field(default_factory=bytes)
    inference_duration: float = 0.0
    
    def __repr__(self) -> str:
        audio_len_ms = len(self.audio_data) / 32 if self.audio_data else 0
        return (
            f"VADEvent(type={self.type.value}, "
            f"speaking={self.speaking}, "
            f"prob={self.probability:.2f}, "
            f"speech={self.speech_duration:.2f}s, "
            f"silence={self.silence_duration:.2f}s, "
            f"audio={audio_len_ms:.0f}ms)"
        )


class ExpFilter:
    """Exponential filter for smoothing probability values
    
    Smooths noisy VAD probability outputs to reduce false triggers.
    Formula: smoothed = alpha * current + (1-alpha) * previous
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


# Mock the Silero model for testing
class MockSileroModel:
    """Mock Silero VAD model that returns predefined probabilities"""
    
    def __init__(self, probabilities: list[float]):
        """
        Args:
            probabilities: List of probability values to return sequentially
        """
        self._probabilities = probabilities
        self._call_index = 0
    
    def __call__(self, audio_tensor, sample_rate):
        """Return next probability in sequence"""
        if self._call_index < len(self._probabilities):
            prob = self._probabilities[self._call_index]
            self._call_index += 1
        else:
            prob = 0.0  # default to silence after sequence
        
        # Return a mock tensor with .item() method
        result = Mock()
        result.item.return_value = prob
        return result
    
    def reset_states(self):
        """Reset model states"""
        pass


@dataclass
class SileroVADOptions:
    """Copy of options for testing"""
    min_speech_duration: float = 0.05       # 50ms to confirm speech start
    min_silence_duration: float = 0.40      # 400ms to confirm speech end
    prefix_padding_duration: float = 0.3    # 300ms prefix padding
    activation_threshold: float = 0.5       # probability threshold
    sample_rate: int = 16000                # 16kHz


class TestSileroVADStream:
    """Test cases demonstrating VAD stream behavior"""
    
    # Silero processes 512 samples per inference (32ms at 16kHz)
    WINDOW_SIZE_SAMPLES = 512
    WINDOW_SIZE_BYTES = 512 * 2  # int16 = 2 bytes per sample
    WINDOW_DURATION = 512 / 16000  # 0.032 seconds
    
    def generate_pcm_silence(self, duration_ms: int) -> bytes:
        """Generate silent PCM audio (zeros)"""
        num_samples = int(duration_ms * 16)  # 16kHz = 16 samples/ms
        return np.zeros(num_samples, dtype=np.int16).tobytes()
    
    def generate_pcm_speech(self, duration_ms: int, amplitude: int = 10000) -> bytes:
        """Generate simulated speech PCM audio (sine wave)"""
        num_samples = int(duration_ms * 16)
        t = np.linspace(0, duration_ms / 1000, num_samples)
        # 440Hz sine wave
        audio = (amplitude * np.sin(2 * np.pi * 440 * t)).astype(np.int16)
        return audio.tobytes()
    
    @pytest.mark.asyncio
    async def test_vad_stream_basic_flow(self):
        """
        Test basic VAD stream flow:
        1. Push silence → no START_OF_SPEECH
        2. Push speech → START_OF_SPEECH after min_speech_duration
        3. Push silence → END_OF_SPEECH after min_silence_duration
        """
        opts = SileroVADOptions()
        
        # Calculate how many windows needed
        # min_speech_duration = 50ms, window = 32ms → need 2 windows above threshold
        # min_silence_duration = 400ms, window = 32ms → need 13 windows below threshold
        windows_for_speech_start = int(opts.min_speech_duration / self.WINDOW_DURATION) + 1  # 2
        windows_for_speech_end = int(opts.min_silence_duration / self.WINDOW_DURATION) + 1  # 13
        
        # Build probability sequence:
        # - 5 windows of silence (prob=0.1)
        # - 3 windows of speech (prob=0.9) → triggers START_OF_SPEECH after 2nd
        # - 15 windows of silence (prob=0.1) → triggers END_OF_SPEECH after 13th
        probs = (
            [0.1] * 5 +          # Initial silence
            [0.9] * 3 +          # Speech detected
            [0.1] * 15           # Silence after speech
        )
        
        print(f"\n{'='*60}")
        print(f"Test: Basic VAD Flow")
        print(f"{'='*60}")
        print(f"Window duration: {self.WINDOW_DURATION*1000:.1f}ms")
        print(f"Windows for speech start: {windows_for_speech_start} "
              f"({opts.min_speech_duration*1000:.0f}ms threshold)")
        print(f"Windows for speech end: {windows_for_speech_end} "
              f"({opts.min_silence_duration*1000:.0f}ms threshold)")
        print(f"Probability sequence: {probs}")
        print()
        
        # Simulate the state machine
        events = await self._simulate_vad_state_machine(probs, opts)
        
        # Print events
        print(f"\nGenerated Events:")
        print(f"-" * 40)
        for i, event in enumerate(events):
            print(f"  [{i}] {event}")
        
        # Verify events
        start_events = [e for e in events if e.type == VADEventType.START_OF_SPEECH]
        end_events = [e for e in events if e.type == VADEventType.END_OF_SPEECH]
        inference_events = [e for e in events if e.type == VADEventType.INFERENCE_DONE]
        
        print(f"\nSummary:")
        print(f"  INFERENCE_DONE: {len(inference_events)}")
        print(f"  START_OF_SPEECH: {len(start_events)}")
        print(f"  END_OF_SPEECH: {len(end_events)}")
        
        assert len(start_events) == 1, "Should have exactly 1 START_OF_SPEECH"
        assert len(end_events) == 1, "Should have exactly 1 END_OF_SPEECH"
        assert start_events[0].speaking == True
        assert end_events[0].speaking == False
    
    @pytest.mark.asyncio
    async def test_vad_prefix_padding(self):
        """
        Test that prefix_padding audio is included in START_OF_SPEECH event.
        
        When speech starts, we want to include 300ms of audio BEFORE the speech
        detection point to capture the beginning of the utterance.
        """
        opts = SileroVADOptions(prefix_padding_duration=0.3)  # 300ms
        
        # Windows before speech starts that should be included as prefix
        prefix_windows = int(opts.prefix_padding_duration / self.WINDOW_DURATION)  # ~10 windows
        
        print(f"\n{'='*60}")
        print(f"Test: Prefix Padding")
        print(f"{'='*60}")
        print(f"Prefix padding: {opts.prefix_padding_duration*1000:.0f}ms "
              f"(~{prefix_windows} windows)")
        
        # Sequence: silence → speech
        probs = [0.1] * 15 + [0.9] * 5  # Long silence then speech
        
        events = await self._simulate_vad_state_machine(probs, opts)
        
        start_events = [e for e in events if e.type == VADEventType.START_OF_SPEECH]
        assert len(start_events) == 1
        
        # Audio in START_OF_SPEECH should include prefix padding
        audio_duration_ms = len(start_events[0].audio_data) / 32  # 16kHz, 16-bit
        expected_min_duration = opts.prefix_padding_duration * 1000  # at least prefix
        
        print(f"Audio in START_OF_SPEECH: {audio_duration_ms:.0f}ms")
        print(f"Expected minimum: {expected_min_duration:.0f}ms (prefix padding)")
        
        assert audio_duration_ms >= expected_min_duration, \
            f"Audio should include prefix padding: {audio_duration_ms:.0f}ms < {expected_min_duration:.0f}ms"
    
    @pytest.mark.asyncio  
    async def test_vad_short_speech_ignored(self):
        """
        Test that very short speech bursts (< min_speech_duration) are ignored.
        
        This prevents false triggers from brief noise.
        """
        opts = SileroVADOptions(min_speech_duration=0.05)  # 50ms
        
        # Only 1 window of "speech" (32ms < 50ms threshold)
        probs = [0.1] * 5 + [0.9] * 1 + [0.1] * 5
        
        print(f"\n{'='*60}")
        print(f"Test: Short Speech Ignored")
        print(f"{'='*60}")
        print(f"Single speech window: {self.WINDOW_DURATION*1000:.0f}ms")
        print(f"Threshold: {opts.min_speech_duration*1000:.0f}ms")
        print(f"Sequence: {probs}")
        
        events = await self._simulate_vad_state_machine(probs, opts)
        
        start_events = [e for e in events if e.type == VADEventType.START_OF_SPEECH]
        
        print(f"START_OF_SPEECH events: {len(start_events)}")
        
        assert len(start_events) == 0, "Short speech should not trigger START_OF_SPEECH"
    
    @pytest.mark.asyncio
    async def test_vad_continuous_speech(self):
        """
        Test continuous speech detection without false end triggers.
        
        Brief silence during speech (< min_silence_duration) should NOT
        trigger END_OF_SPEECH.
        """
        opts = SileroVADOptions(
            min_speech_duration=0.05,
            min_silence_duration=0.40
        )
        
        # Speech → brief silence (3 windows = 96ms) → speech again
        brief_silence_windows = 3  # 96ms < 400ms threshold
        
        probs = (
            [0.1] * 3 +           # Initial silence  
            [0.9] * 5 +           # Speech starts
            [0.1] * brief_silence_windows +  # Brief pause (should NOT end speech)
            [0.9] * 5 +           # Speech continues
            [0.1] * 15            # Final silence (should end speech)
        )
        
        print(f"\n{'='*60}")
        print(f"Test: Continuous Speech with Brief Pause")
        print(f"{'='*60}")
        print(f"Brief pause: {brief_silence_windows * self.WINDOW_DURATION * 1000:.0f}ms")
        print(f"min_silence_duration: {opts.min_silence_duration*1000:.0f}ms")
        
        events = await self._simulate_vad_state_machine(probs, opts)
        
        end_events = [e for e in events if e.type == VADEventType.END_OF_SPEECH]
        
        print(f"END_OF_SPEECH events: {len(end_events)}")
        
        # Should only have ONE end event (at the final silence)
        assert len(end_events) == 1, \
            "Brief pause should not trigger END_OF_SPEECH"
    
    @pytest.mark.asyncio
    async def test_vad_exp_filter_smoothing(self):
        """
        Test exponential filter smoothing effect.
        
        The ExpFilter smooths probability values to reduce false triggers:
        smoothed = alpha * current + (1-alpha) * previous
        """
        print(f"\n{'='*60}")
        print(f"Test: Exponential Filter Smoothing")
        print(f"{'='*60}")
        
        exp_filter = ExpFilter(alpha=0.35)
        
        # Simulate noisy probability sequence
        raw_probs = [0.1, 0.9, 0.2, 0.8, 0.3, 0.7, 0.1, 0.1, 0.1]
        smoothed_probs = []
        
        print(f"Alpha: {exp_filter._alpha}")
        print(f"{'Raw':<8} {'Smoothed':<10}")
        print(f"-" * 20)
        
        for prob in raw_probs:
            smoothed = exp_filter.apply(prob)
            smoothed_probs.append(smoothed)
            print(f"{prob:<8.2f} {smoothed:<10.3f}")
        
        # Smoothed values should be less volatile
        raw_variance = np.var(raw_probs)
        smoothed_variance = np.var(smoothed_probs)
        
        print(f"\nVariance - Raw: {raw_variance:.3f}, Smoothed: {smoothed_variance:.3f}")
        
        assert smoothed_variance < raw_variance, \
            "Smoothed signal should have lower variance"
    
    async def _simulate_vad_state_machine(
        self, 
        probabilities: list[float], 
        opts: SileroVADOptions
    ) -> list[VADEvent]:
        """
        Simulate the Silero VAD state machine logic.
        
        This replicates the core logic from SileroVADStream._run_task()
        without needing the actual model or audio processing.
        """
        events = []
        exp_filter = ExpFilter(alpha=0.35)
        
        # State variables
        pub_speaking = False
        pub_speech_duration = 0.0
        pub_silence_duration = 0.0
        speech_threshold_duration = 0.0
        silence_threshold_duration = 0.0
        
        # Speech buffer simulation
        speech_buffer_index = 0
        prefix_padding_bytes = int(opts.prefix_padding_duration * opts.sample_rate) * 2
        
        for prob in probabilities:
            # Apply exponential smoothing
            smoothed_prob = exp_filter.apply(prob)
            
            # Simulate writing audio to buffer
            speech_buffer_index += self.WINDOW_SIZE_BYTES
            
            # Update durations
            if pub_speaking:
                pub_speech_duration += self.WINDOW_DURATION
            else:
                pub_silence_duration += self.WINDOW_DURATION
            
            # Generate fake audio data based on buffer index
            audio_data = bytes(speech_buffer_index)
            
            # Emit INFERENCE_DONE
            events.append(VADEvent(
                type=VADEventType.INFERENCE_DONE,
                probability=smoothed_prob,
                speech_duration=pub_speech_duration,
                silence_duration=pub_silence_duration,
                speaking=pub_speaking,
                audio_data=audio_data,
                inference_duration=0.001,
            ))
            
            # State machine logic
            if smoothed_prob >= opts.activation_threshold:
                speech_threshold_duration += self.WINDOW_DURATION
                silence_threshold_duration = 0.0
                
                if not pub_speaking:
                    if speech_threshold_duration >= opts.min_speech_duration:
                        pub_speaking = True
                        pub_silence_duration = 0.0
                        pub_speech_duration = speech_threshold_duration
                        
                        # Emit START_OF_SPEECH
                        events.append(VADEvent(
                            type=VADEventType.START_OF_SPEECH,
                            probability=smoothed_prob,
                            speech_duration=pub_speech_duration,
                            silence_duration=0.0,
                            speaking=True,
                            audio_data=audio_data,
                            inference_duration=0.001,
                        ))
            else:
                silence_threshold_duration += self.WINDOW_DURATION
                speech_threshold_duration = 0.0
                
                if not pub_speaking:
                    # Reset buffer (keep prefix padding)
                    if speech_buffer_index > prefix_padding_bytes:
                        speech_buffer_index = prefix_padding_bytes
                
                if pub_speaking and silence_threshold_duration >= opts.min_silence_duration:
                    pub_speaking = False
                    pub_silence_duration = silence_threshold_duration
                    
                    # Emit END_OF_SPEECH
                    events.append(VADEvent(
                        type=VADEventType.END_OF_SPEECH,
                        probability=smoothed_prob,
                        speech_duration=pub_speech_duration,
                        silence_duration=pub_silence_duration,
                        speaking=False,
                        audio_data=audio_data,
                        inference_duration=0.001,
                    ))
                    
                    pub_speech_duration = 0.0
                    speech_buffer_index = prefix_padding_bytes
        
        return events


class TestVADBufferManagement:
    """Test cases for buffer management logic"""
    
    @pytest.mark.asyncio
    async def test_buffer_reset_keeps_prefix(self):
        """
        Test that _reset_write_cursor keeps the last prefix_padding bytes.
        
        This is crucial for capturing the beginning of speech:
        
        Before reset: [old audio][prefix padding][new audio]
        After reset:  [prefix padding]
        """
        print(f"\n{'='*60}")
        print(f"Test: Buffer Reset Keeps Prefix")
        print(f"{'='*60}")
        
        prefix_duration = 0.3  # 300ms
        sample_rate = 16000
        prefix_padding_bytes = int(prefix_duration * sample_rate) * 2
        
        # Simulate buffer
        max_speech_bytes = 60 * sample_rate * 2 + prefix_padding_bytes
        speech_buffer = bytearray(max_speech_bytes)
        
        # Fill buffer with identifiable data
        # [AAAA][BBBB][CCCC] where BBBB is the last prefix_padding worth
        total_fill = prefix_padding_bytes * 3
        for i in range(total_fill):
            if i < prefix_padding_bytes:
                speech_buffer[i] = ord('A')
            elif i < prefix_padding_bytes * 2:
                speech_buffer[i] = ord('B')
            else:
                speech_buffer[i] = ord('C')
        
        speech_buffer_index = total_fill
        
        print(f"Buffer before reset:")
        print(f"  Index: {speech_buffer_index}")
        print(f"  Content pattern: [AAA...][BBB...][CCC...]")
        
        # Simulate _reset_write_cursor
        if speech_buffer_index > prefix_padding_bytes:
            padding_data = speech_buffer[
                speech_buffer_index - prefix_padding_bytes : speech_buffer_index
            ]
            speech_buffer[: prefix_padding_bytes] = padding_data
            speech_buffer_index = prefix_padding_bytes
        
        print(f"\nBuffer after reset:")
        print(f"  Index: {speech_buffer_index}")
        print(f"  First byte: {chr(speech_buffer[0])}")
        
        # Verify the last chunk (CCCC) is now at the beginning
        assert speech_buffer_index == prefix_padding_bytes
        assert speech_buffer[0] == ord('C'), \
            "Reset should keep last prefix_padding bytes (CCCC)"


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])

