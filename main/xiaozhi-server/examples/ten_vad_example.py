#!/usr/bin/env python3
"""
Example usage of TEN VAD in XiaoZhi ESP32 Server
This example shows how to use TEN VAD for voice activity detection
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def example_ten_vad_usage():
    """Example of how to use TEN VAD"""
    
    print("🎤 TEN VAD Usage Example")
    print("=" * 40)
    
    # Import the TEN VAD provider
    from core.providers.vad.ten_vad import VADProvider
    
    # Configuration for TEN VAD
    config = {
        "model_path": "models/ten-vad",
        "sample_rate": 16000,
        "frame_size": 512,
        "threshold": 0.5,          # High threshold for voice detection
        "threshold_low": 0.2,      # Low threshold for voice detection  
        "min_silence_duration_ms": 1000,  # 1 second of silence to end speech
        "frame_window_threshold": 3        # Need 3 positive frames for voice
    }
    
    print("📋 Configuration:")
    for key, value in config.items():
        print(f"   {key}: {value}")
    
    # Create VAD provider instance
    print("\n🔧 Creating TEN VAD provider...")
    try:
        vad_provider = VADProvider(config)
        print("✅ TEN VAD provider created successfully")
    except Exception as e:
        print(f"❌ Failed to create TEN VAD provider: {e}")
        return False
    
    # Mock connection object (in real usage, this comes from the WebSocket connection)
    class MockConnection:
        def __init__(self):
            self.client_audio_buffer = bytearray()
            self.client_voice_window = []
            self.last_is_voice = False
            self.client_have_voice = False
            self.last_activity_time = 0
            self.client_voice_stop = False
    
    print("\n🔗 Creating mock connection...")
    conn = MockConnection()
    
    print("\n📝 Usage Notes:")
    print("   • In real usage, opus_packet would contain actual Opus-encoded audio")
    print("   • The VAD provider processes audio in real-time")
    print("   • Voice detection uses dual thresholds for stability")
    print("   • Sliding window prevents false positives")
    
    print("\n💡 Integration Tips:")
    print("   1. Update .config.yaml to use TEN VAD:")
    print("      selected_module:")
    print("        VAD: TenVAD")
    print()
    print("   2. Adjust thresholds based on your environment:")
    print("      • Noisy environment: Higher thresholds")
    print("      • Quiet environment: Lower thresholds")
    print()
    print("   3. Tune silence duration for your use case:")
    print("      • Quick responses: Lower min_silence_duration_ms")
    print("      • Patient listening: Higher min_silence_duration_ms")
    
    return True

def show_configuration_options():
    """Show different configuration options for TEN VAD"""
    
    print("\n🎛️  Configuration Options")
    print("=" * 40)
    
    configs = {
        "Sensitive (Good for quiet environments)": {
            "threshold": 0.3,
            "threshold_low": 0.1,
            "frame_window_threshold": 2,
            "min_silence_duration_ms": 800
        },
        "Balanced (Default settings)": {
            "threshold": 0.5,
            "threshold_low": 0.2,
            "frame_window_threshold": 3,
            "min_silence_duration_ms": 1000
        },
        "Conservative (Good for noisy environments)": {
            "threshold": 0.7,
            "threshold_low": 0.4,
            "frame_window_threshold": 4,
            "min_silence_duration_ms": 1200
        }
    }
    
    for name, config in configs.items():
        print(f"\n📊 {name}:")
        for key, value in config.items():
            print(f"   {key}: {value}")

def main():
    """Main example function"""
    
    # Run the basic usage example
    if not example_ten_vad_usage():
        return False
    
    # Show configuration options
    show_configuration_options()
    
    print("\n" + "=" * 50)
    print("✅ TEN VAD example completed!")
    print("\nNext steps:")
    print("1. Install TEN VAD: python scripts/install_ten_vad.py")
    print("2. Test installation: python scripts/test_ten_vad.py")
    print("3. Update your .config.yaml to use TEN VAD")
    print("4. Start the server and test with real audio")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)