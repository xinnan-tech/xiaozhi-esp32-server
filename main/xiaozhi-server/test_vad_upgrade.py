"""Test script for the upgraded VAD implementation."""

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


def test_vad_implementation():
    """Test the VAD implementation with sample audio."""
    
    print("Testing VAD Implementation...")
    
    # Test configuration
    config = {
        "model_dir": "models/snakers4_silero-vad",
        "threshold": "0.5",
        "threshold_low": "0.2", 
        "min_silence_duration_ms": "1000",
        "frame_window_threshold": 3,
        "start_secs": "0.2",
        "stop_secs": "0.8",
        "min_volume": "0.6"
    }
    
    try:
        # Try to import and test the VAD
        from core.providers.vad.silero import VADProvider
        
        print("Creating VAD provider...")
        vad = VADProvider(config)
        
        # Check which implementation was loaded
        if hasattr(vad, 'analyzer'):
            print("✓ ONNX-based VAD loaded successfully!")
            print(f"  - VAD State: {vad.analyzer._vad_state.name}")
            print(f"  - Sample Rate: {vad.analyzer.sample_rate}")
            print(f"  - Params: {vad.analyzer.params}")
        else:
            print("✓ PyTorch-based VAD loaded (fallback)")
            
        # Create mock connection
        conn = MockConnection()
        
        # Generate test audio (silence)
        print("\nTesting with silent audio...")
        silent_opus = b'\xf8\xff\xfe' * 60  # Mock silent Opus packet
        
        # Test VAD with silent audio
        result = vad.is_vad(conn, silent_opus)
        print(f"  - Voice detected: {result}")
        print(f"  - Connection voice state: {conn.client_have_voice}")
        
        print("\nVAD test completed successfully!")
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        print("  Make sure all dependencies are installed")
    except Exception as e:
        print(f"✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()


def test_vad_analyzer_directly():
    """Test the VAD analyzer component directly."""
    
    print("\n\nTesting VAD Analyzer directly...")
    
    try:
        from core.providers.vad.vad_analyzer import VADAnalyzer, VADParams, VADState
        from core.providers.vad.silero_onnx import SileroVADAnalyzer
        
        # Check if ONNX model exists
        model_path = "models/snakers4_silero-vad/src/silero_vad/data/silero_vad.onnx"
        import os
        
        if not os.path.exists(model_path):
            print(f"✗ ONNX model not found at: {model_path}")
            return
            
        print(f"✓ ONNX model found at: {model_path}")
        
        # Create analyzer
        params = VADParams(
            confidence=0.5,
            start_secs=0.2,
            stop_secs=0.8,
            min_volume=0.6
        )
        
        analyzer = SileroVADAnalyzer(
            model_path=model_path,
            sample_rate=16000,
            params=params
        )
        
        print(f"✓ Analyzer created successfully")
        print(f"  - Initial state: {analyzer._vad_state.name}")
        print(f"  - Frames required: {analyzer.num_frames_required()}")
        
        # Generate test audio (512 samples = 1024 bytes for 16kHz)
        silent_audio = np.zeros(512, dtype=np.int16).tobytes()
        
        # Process multiple frames
        print("\nProcessing audio frames...")
        for i in range(5):
            state = analyzer.analyze_audio(silent_audio)
            print(f"  Frame {i+1}: State = {state.name}")
            
        print("\nVAD Analyzer test completed!")
        
    except Exception as e:
        print(f"✗ Error testing analyzer: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_vad_implementation()
    test_vad_analyzer_directly()