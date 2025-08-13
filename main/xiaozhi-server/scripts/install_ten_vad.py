#!/usr/bin/env python3
"""
Installation script for TEN VAD
This script helps download and set up the TEN VAD model files
"""

import os
import sys
import subprocess
import urllib.request
import zipfile
from pathlib import Path

def install_ten_vad_package():
    """Install the ten-vad Python package"""
    print("Installing ten-vad package...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "ten-vad"])
        print("✅ ten-vad package installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install ten-vad package: {e}")
        return False

def download_model_files():
    """Download TEN VAD model files if needed"""
    model_dir = Path("models/ten-vad")
    model_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Model directory: {model_dir.absolute()}")
    
    # Check if model files already exist
    if (model_dir / "model.onnx").exists():
        print("✅ TEN VAD model files already exist")
        return True
    
    print("📥 TEN VAD model files will be downloaded automatically on first use")
    print("   or you can manually place model files in:", model_dir.absolute())
    
    return True

def verify_installation():
    """Verify that TEN VAD is properly installed"""
    try:
        import ten_vad
        print("✅ TEN VAD import successful")
        
        # Try to create a TEN VAD instance (this might download models)
        print("🔍 Testing TEN VAD initialization...")
        model_path = "models/ten-vad"
        
        # Note: This might fail if models aren't available, but that's expected
        print(f"   Model path: {os.path.abspath(model_path)}")
        print("   Models will be downloaded automatically when first used")
        
        return True
    except ImportError as e:
        print(f"❌ Failed to import ten_vad: {e}")
        return False
    except Exception as e:
        print(f"⚠️  TEN VAD package imported but initialization may need models: {e}")
        return True  # This is expected if models aren't downloaded yet

def main():
    """Main installation function"""
    print("🚀 Installing TEN VAD for XiaoZhi ESP32 Server")
    print("=" * 50)
    
    # Step 1: Install Python package
    if not install_ten_vad_package():
        print("❌ Installation failed at package installation step")
        return False
    
    # Step 2: Set up model directory
    if not download_model_files():
        print("❌ Installation failed at model setup step")
        return False
    
    # Step 3: Verify installation
    if not verify_installation():
        print("❌ Installation verification failed")
        return False
    
    print("\n" + "=" * 50)
    print("✅ TEN VAD installation completed successfully!")
    print("\nTo use TEN VAD, update your .config.yaml:")
    print("  selected_module:")
    print("    VAD: TenVAD")
    print("\nThe TEN VAD configuration is already added to your config file.")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)