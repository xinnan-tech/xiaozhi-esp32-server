"""Test script to verify VAD state reset functionality."""

import numpy as np
import time
from collections import deque

# Mock connection class for testing
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
        """Reset VAD states including internal provider states."""
        self.client_audio_buffer = bytearray()
        self.client_have_voice = False
        self.client_voice_stop = False
        # Reset VAD provider internal states
        if hasattr(self, 'vad') and self.vad is not None:
            self.vad.reset()


def test_vad_reset():
    """Test VAD state reset functionality."""
    
    print("Testing VAD State Reset Functionality...")
    
    # Test configuration
    config = {
        "model_dir": "models/snakers4_silero-vad",
        "threshold": "0.5",
        "min_silence_duration_ms": "1000",
        "frame_window_threshold": 3,
        "start_secs": "0.2",
        "stop_secs": "0.8",
        "min_volume": "0.6"
    }
    
    try:
        from core.providers.vad.silero import VADProvider
        from core.providers.vad.vad_analyzer import VADState
        
        # Create VAD provider
        print("\n1. Creating VAD provider...")
        vad = VADProvider(config)
        
        # Create mock connection
        conn = MockConnection()
        conn.vad = vad
        
        # Check initial state
        if hasattr(vad, 'analyzer'):
            print(f"   Initial VAD state: {vad.analyzer._vad_state.name}")
            print(f"   Initial buffer size: {len(vad.analyzer._vad_buffer)}")
            
            # Simulate some audio processing to change state
            print("\n2. Processing some audio to change state...")
            # Generate test audio with voice (non-zero values)
            voice_audio = (np.random.randn(512) * 1000).astype(np.int16).tobytes()
            
            # Process multiple frames to potentially change state
            for i in range(5):
                state = vad.analyzer.analyze_audio(voice_audio)
                print(f"   Frame {i+1}: State = {state.name}")
            
            # Check state after processing
            print(f"\n3. State after processing: {vad.analyzer._vad_state.name}")
            print(f"   Buffer size: {len(vad.analyzer._vad_buffer)}")
            print(f"   Starting count: {vad.analyzer._vad_starting_count}")
            print(f"   Stopping count: {vad.analyzer._vad_stopping_count}")
            
            # Reset VAD states
            print("\n4. Resetting VAD states...")
            conn.reset_vad_states()
            
            # Check state after reset
            print(f"\n5. State after reset: {vad.analyzer._vad_state.name}")
            print(f"   Buffer size: {len(vad.analyzer._vad_buffer)}")
            print(f"   Starting count: {vad.analyzer._vad_starting_count}")
            print(f"   Stopping count: {vad.analyzer._vad_stopping_count}")
            
            # Verify reset worked
            if (vad.analyzer._vad_state == VADState.QUIET and 
                len(vad.analyzer._vad_buffer) == 0 and
                vad.analyzer._vad_starting_count == 0 and
                vad.analyzer._vad_stopping_count == 0):
                print("\n✓ VAD state reset successful!")
            else:
                print("\n✗ VAD state reset failed!")
                
        else:
            print("✗ ONNX VAD not loaded (using PyTorch fallback)")
            
    except Exception as e:
        print(f"✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()


def test_model_state_reset():
    """Test that model states are also reset."""
    
    print("\n\nTesting Model State Reset...")
    
    try:
        from core.providers.vad.silero_onnx import SileroOnnxModel
        import os
        
        model_path = "models/snakers4_silero-vad/src/silero_vad/data/silero_vad.onnx"
        
        if not os.path.exists(model_path):
            print(f"✗ ONNX model not found at: {model_path}")
            return
            
        # Create model
        model = SileroOnnxModel(model_path)
        
        # Check initial state
        print(f"1. Initial model state shape: {model._state.shape}")
        print(f"   Initial context shape: {model._context.shape}")
        
        # Process some audio to change state
        audio = np.random.randn(512).astype(np.float32)
        result = model(audio, 16000)
        
        print(f"\n2. After processing:")
        print(f"   State shape: {model._state.shape}")
        print(f"   Context shape: {model._context.shape}")
        
        # Reset states
        model.reset_states()
        
        print(f"\n3. After reset:")
        print(f"   State shape: {model._state.shape}")
        print(f"   Context shape: {model._context.shape}")
        print(f"   State is zeros: {np.allclose(model._state, 0)}")
        
        print("\n✓ Model state reset test completed!")
        
    except Exception as e:
        print(f"✗ Error testing model reset: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_vad_reset()
    test_model_state_reset()