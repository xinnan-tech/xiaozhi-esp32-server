#!/usr/bin/env python3
"""
Install huggingface_hub for better model downloads
"""

import subprocess
import sys

def install_huggingface_hub():
    """Install huggingface_hub package"""
    try:
        print("Installing huggingface_hub...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "huggingface_hub"
        ])
        print("✅ huggingface_hub installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install huggingface_hub: {e}")
        return False

if __name__ == "__main__":
    success = install_huggingface_hub()
    if success:
        print("\n🎉 You can now use Hugging Face models for better reliability!")
        print("The system will automatically fallback to ModelScope if needed.")
    else:
        print("\n⚠️  Installation failed, but the system will still work with ModelScope.")