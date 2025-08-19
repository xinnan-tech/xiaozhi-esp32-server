"""Test VAD state transitions and reset with realistic audio."""

import numpy as np
import time
from core.providers.vad.vad_analyzer import VADState, VADParams

def test_vad_state_transitions():
    """Test VAD state transitions with loud audio."""
    
    print("Testing VAD State Transitions with Loud Audio...")
    
    try:
        from core.providers.vad.silero_onnx import SileroVADAnalyzer
        import os
        
        model_path = "models/snakers4_silero-vad/src/silero_vad/data/silero_vad.onnx"
        
        if not os.path.exists(model_path):
            print(f"✗ ONNX model not found at: {model_path}")
            return
            
        # Create analyzer with lower thresholds for testing
        params = VADParams(
            confidence=0.3,  # Lower confidence threshold
            start_secs=0.1,  # Faster start
            stop_secs=0.2,   # Faster stop
            min_volume=0.1   # Lower volume threshold
        )
        
        analyzer = SileroVADAnalyzer(
            model_path=model_path,
            sample_rate=16000,
            params=params
        )
        
        print(f"Initial state: {analyzer._vad_state.name}")
        
        # Generate loud "voice" audio (high amplitude sine wave)
        print("\n1. Testing with loud audio (simulated voice)...")
        frequency = 440  # A4 note
        duration_samples = 512
        t = np.linspace(0, duration_samples/16000, duration_samples)
        # Generate loud sine wave (80% of max amplitude)
        loud_audio = (0.8 * 32767 * np.sin(2 * np.pi * frequency * t)).astype(np.int16).tobytes()
        
        # Process multiple frames of loud audio
        for i in range(10):
            state = analyzer.analyze_audio(loud_audio)
            print(f"   Frame {i+1}: State = {state.name}, " +
                  f"Starting count = {analyzer._vad_starting_count}, " +
                  f"Stopping count = {analyzer._vad_stopping_count}")
            if state == VADState.SPEAKING:
                print("   ✓ Voice detected!")
                break
        
        # Now test with silence
        print("\n2. Testing with silence...")
        silent_audio = np.zeros(512, dtype=np.int16).tobytes()
        
        for i in range(10):
            state = analyzer.analyze_audio(silent_audio)
            print(f"   Frame {i+1}: State = {state.name}, " +
                  f"Starting count = {analyzer._vad_starting_count}, " +
                  f"Stopping count = {analyzer._vad_stopping_count}")
            if state == VADState.QUIET:
                print("   ✓ Silence detected!")
                break
        
        # Check final state
        print(f"\n3. Final state before reset: {analyzer._vad_state.name}")
        
        # Reset
        print("\n4. Resetting analyzer...")
        analyzer.reset()
        
        print(f"   State after reset: {analyzer._vad_state.name}")
        print(f"   All counters zero: {analyzer._vad_starting_count == 0 and analyzer._vad_stopping_count == 0}")
        
        # Test that it works again after reset
        print("\n5. Testing detection works after reset...")
        state = analyzer.analyze_audio(loud_audio)
        print(f"   First frame after reset: {state.name}")
        
        print("\n✓ State transition test completed!")
        
    except Exception as e:
        print(f"✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()


def test_real_world_scenario():
    """Test a real-world scenario with connection reset."""
    
    print("\n\nTesting Real-World Scenario...")
    
    try:
        from core.providers.vad.silero import VADProvider
        from collections import deque
        
        # Mock connection
        class MockConnection:
            def __init__(self):
                self.client_audio_buffer = bytearray()
                self.client_voice_window = deque(maxlen=5)
                self.last_is_voice = False
                self.client_have_voice = False
                self.last_activity_time = 0.0
                self.client_voice_stop = False
                self.vad = None
                
            def reset_vad_states(self):
                self.client_audio_buffer = bytearray()
                self.client_have_voice = False
                self.client_voice_stop = False
                if hasattr(self, 'vad') and self.vad is not None:
                    self.vad.reset()
        
        # Create VAD with normal config
        config = {
            "threshold": "0.4",
            "min_silence_duration_ms": "1000",
            "start_secs": "0.2",
            "stop_secs": "0.8",
            "min_volume": "0.3"
        }
        
        vad = VADProvider(config)
        conn = MockConnection()
        conn.vad = vad
        
        print("1. Simulating first conversation...")
        # Mock Opus packet (normally would be real encoded audio)
        mock_opus = b'\xf8\xff\xfe' * 60
        
        # Process some "audio"
        for i in range(3):
            result = vad.is_vad(conn, mock_opus)
            print(f"   Frame {i+1}: VAD result = {result}")
        
        if hasattr(vad, 'analyzer'):
            print(f"   Final state: {vad.analyzer._vad_state.name}")
        
        print("\n2. Resetting for new conversation...")
        conn.reset_vad_states()
        
        if hasattr(vad, 'analyzer'):
            print(f"   State after reset: {vad.analyzer._vad_state.name}")
            print(f"   Clean slate: {vad.analyzer._vad_state == VADState.QUIET}")
        
        print("\n✓ Real-world scenario test completed!")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_vad_state_transitions()
    test_real_world_scenario()