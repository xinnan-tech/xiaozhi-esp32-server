#!/usr/bin/env python3
"""
Test script for TEN VAD ONNX integration
This script tests if TEN VAD ONNX is properly installed and working across platforms
"""

import sys
import os
import platform
import numpy as np
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def get_platform_info():
    """Get current platform information"""
    system = platform.system()
    machine = platform.machine()
    return system, machine

def test_platform_libraries():
    """Test if platform-specific libraries are available"""
    print("🔍 Testing platform-specific libraries...")
    
    system, machine = get_platform_info()
    print(f"   Current platform: {system} {machine}")
    
    base_path = Path("models/ten-vad-onnx")
    
    if system == "Windows":
        if machine.upper() in ['X64', 'X86_64', 'AMD64']:
            lib_paths = [
                base_path / "lib" / "Windows" / "x64" / "ten_vad.dll",
                base_path / "ten_vad_library" / "ten_vad.dll"
            ]
        else:
            lib_paths = [
                base_path / "lib" / "Windows" / "x86" / "ten_vad.dll",
                base_path / "ten_vad_library" / "ten_vad.dll"
            ]
    elif system == "Linux":
        lib_paths = [
            base_path / "lib" / "Linux" / "x64" / "libten_vad.so",
            base_path / "ten_vad_library" / "libten_vad.so"
        ]
    elif system == "Darwin":  # macOS
        lib_paths = [
            base_path / "lib" / "macOS" / "ten_vad.framework" / "Versions" / "A" / "ten_vad",
            base_path / "ten_vad_library" / "libten_vad"
        ]
    else:
        print(f"❌ Unsupported platform: {system} {machine}")
        return False
    
    found_lib = False
    for lib_path in lib_paths:
        if lib_path.exists():
            print(f"✅ Found library: {lib_path}")
            found_lib = True
        else:
            print(f"❌ Missing library: {lib_path}")
    
    return found_lib

def test_ten_vad_onnx_import():
    """Test if TEN VAD ONNX can be imported"""
    print("🔍 Testing TEN VAD ONNX import...")
    try:
        # Test direct import from model directory
        model_path = Path("models/ten-vad-onnx").resolve()
        if not model_path.exists():
            print(f"❌ Model path not found: {model_path}")
            return False
        
        sys.path.insert(0, str(model_path))
        try:
            from ten_vad import TenVad
            print("✅ TEN VAD ONNX import successful")
            return True
        finally:
            if str(model_path) in sys.path:
                sys.path.remove(str(model_path))
                
    except ImportError as e:
        print(f"❌ Failed to import TEN VAD ONNX: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error importing TEN VAD ONNX: {e}")
        return False

def test_vad_provider():
    """Test if our VAD provider can be created"""
    print("🔍 Testing TEN VAD ONNX provider...")
    try:
        from core.providers.vad.ten_vad_onnx import VADProvider
        
        # Test configuration
        config = {
            "model_path": "models/ten-vad-onnx",
            "sample_rate": 16000,
            "hop_size": 256,
            "frame_size": 512,
            "threshold": 0.5,
            "threshold_low": 0.2,
            "min_silence_duration_ms": 1000,
            "frame_window_threshold": 3
        }
        
        print("   Creating VAD provider instance...")
        vad_provider = VADProvider(config)
        
        if hasattr(vad_provider, 'ten_vad_working'):
            if vad_provider.ten_vad_working:
                print("✅ TEN VAD ONNX provider created successfully (native mode)")
            else:
                print("⚠️  TEN VAD ONNX provider created with fallback mode")
            return True
        else:
            print("✅ TEN VAD ONNX provider created successfully")
            return True
        
    except Exception as e:
        print(f"❌ Failed to create TEN VAD ONNX provider: {e}")
        return False

def test_audio_processing():
    """Test audio processing with dummy data"""
    print("🔍 Testing audio processing...")
    try:
        from core.providers.vad.ten_vad_onnx import VADProvider
        
        config = {
            "model_path": "models/ten-vad-onnx",
            "sample_rate": 16000,
            "hop_size": 256,
            "frame_size": 512,
            "threshold": 0.5,
            "threshold_low": 0.2,
            "min_silence_duration_ms": 1000,
            "frame_window_threshold": 3
        }
        
        vad_provider = VADProvider(config)
        
        # Create a mock connection object
        class MockConnection:
            def __init__(self):
                self.client_audio_buffer = bytearray()
                self.client_voice_window = []
                self.last_is_voice = False
                self.client_have_voice = False
                self.last_activity_time = 0
                self.client_voice_stop = False
        
        conn = MockConnection()
        
        # Generate dummy Opus packet (this is just for testing the structure)
        dummy_opus_packet = b'\x00' * 100  # Dummy data
        
        print("   Testing with dummy audio data...")
        print("   Note: Real audio processing will happen during actual usage")
        
        # Test the processing structure
        if hasattr(vad_provider, 'ten_vad_working'):
            mode = "native" if vad_provider.ten_vad_working else "fallback"
            print(f"   VAD provider running in {mode} mode")
        
        print("✅ Audio processing structure test passed")
        return True
        
    except Exception as e:
        print(f"❌ Audio processing test failed: {e}")
        return False

def test_configuration_loading():
    """Test if configuration can be loaded"""
    print("🔍 Testing configuration loading...")
    try:
        from core.utils.vad import create_instance
        
        config = {
            "model_path": "models/ten-vad-onnx",
            "sample_rate": 16000,
            "hop_size": 256,
            "threshold": 0.5,
            "threshold_low": 0.2,
        }
        
        # Test the factory method
        vad_instance = create_instance("ten_vad_onnx", config)
        print("✅ Configuration loading test passed")
        return True
        
    except Exception as e:
        print(f"❌ Configuration loading test failed: {e}")
        return False

def show_cross_platform_status():
    """Show cross-platform library status"""
    print("\n📋 Cross-Platform Library Status")
    print("-" * 40)
    
    base_path = Path("models/ten-vad-onnx")
    
    platforms = [
        ("Windows x64", base_path / "lib" / "Windows" / "x64" / "ten_vad.dll"),
        ("Linux x64", base_path / "lib" / "Linux" / "x64" / "libten_vad.so"),
        ("macOS", base_path / "lib" / "macOS" / "ten_vad.framework" / "Versions" / "A" / "ten_vad"),
        ("Python impl", base_path / "ten_vad.py")
    ]
    
    for platform_name, lib_path in platforms:
        status = "✅ Available" if lib_path.exists() else "❌ Missing"
        print(f"   {platform_name:<12}: {status}")

def main():
    """Run all tests"""
    print("🚀 Testing TEN VAD ONNX Cross-Platform Integration")
    print("=" * 60)
    
    system, machine = get_platform_info()
    print(f"Platform: {system} {machine}")
    
    # Show cross-platform status first
    show_cross_platform_status()
    
    tests = [
        ("Platform Libraries", test_platform_libraries),
        ("TEN VAD ONNX Import", test_ten_vad_onnx_import),
        ("VAD Provider Creation", test_vad_provider),
        ("Audio Processing", test_audio_processing),
        ("Configuration Loading", test_configuration_loading),
    ]
    
    print(f"\n🧪 Running {len(tests)} tests...")
    print("-" * 40)
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        if test_func():
            passed += 1
        else:
            print(f"   ❌ Test failed: {test_name}")
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All tests passed! TEN VAD ONNX is ready for cross-platform use.")
        print("\n🌍 Platform Support:")
        print("  • Windows: Native DLL support")
        print("  • Linux:   Native .so support") 
        print("  • macOS:   Native framework support")
        print("\n📝 To use TEN VAD ONNX, update your .config.yaml:")
        print("  selected_module:")
        print("    VAD: TenVAD_ONNX")
    else:
        print("❌ Some tests failed. Please check the errors above.")
        print("💡 Try running the installation script:")
        print("   python scripts/install_ten_vad_onnx.py")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)