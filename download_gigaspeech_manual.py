#!/usr/bin/env python3
"""
Manual download script for Gigaspeech model
Use this if the automatic download fails
"""

import os
import urllib.request
import tarfile

def download_gigaspeech_manual():
    """Manually download and extract Gigaspeech model"""
    
    url = "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-zipformer-gigaspeech-2023-12-12.tar.bz2"
    model_dir = "models/sherpa-onnx-zipformer-gigaspeech-2023-12-12"
    
    print("🔽 Manual Gigaspeech Model Download")
    print("=" * 50)
    
    # Check if already exists
    expected_files = [
        "encoder-epoch-30-avg-9.onnx",
        "decoder-epoch-30-avg-9.onnx", 
        "joiner-epoch-30-avg-9.onnx",
        "tokens.txt"
    ]
    
    if all(os.path.exists(os.path.join(model_dir, f)) for f in expected_files):
        print("✅ Model already exists!")
        return True
    
    try:
        # Create models directory
        os.makedirs("models", exist_ok=True)
        
        # Download file
        tar_filename = "models/gigaspeech_temp.tar.bz2"
        print(f"📥 Downloading from: {url}")
        print("⏳ This may take a few minutes (~120MB)...")
        
        def progress_hook(block_num, block_size, total_size):
            if total_size > 0:
                percent = min(100, (block_num * block_size * 100) // total_size)
                print(f"\r📊 Progress: {percent}%", end="", flush=True)
        
        urllib.request.urlretrieve(url, tar_filename, progress_hook)
        print("\n✅ Download completed!")
        
        # Extract
        print("📂 Extracting files...")
        with tarfile.open(tar_filename, 'r:bz2') as tar:
            tar.extractall("models")
        
        # Clean up
        os.remove(tar_filename)
        
        # Verify
        if all(os.path.exists(os.path.join(model_dir, f)) for f in expected_files):
            print("✅ Extraction successful!")
            print("\n📁 Model files:")
            for f in expected_files:
                file_path = os.path.join(model_dir, f)
                size = os.path.getsize(file_path) / (1024*1024)  # MB
                print(f"   ✓ {f}: {size:.1f} MB")
            
            print(f"\n🎉 Gigaspeech model ready!")
            print(f"📍 Location: {os.path.abspath(model_dir)}")
            print("\n🚀 You can now start your server with:")
            print("   python app.py")
            
            return True
        else:
            print("❌ Some files are missing after extraction")
            return False
            
    except Exception as e:
        print(f"❌ Download failed: {e}")
        return False

if __name__ == "__main__":
    print("Manual Gigaspeech Model Downloader")
    print("Use this if automatic download fails")
    print()
    
    success = download_gigaspeech_manual()
    
    if success:
        print("\n🎯 SUCCESS! Your English-only ASR model is ready!")
        print("✅ 100% English-only")
        print("✅ Large vocabulary (GigaSpeech)")
        print("✅ Perfect for multiple kids")
        print("✅ Fast Zipformer architecture")
    else:
        print("\n⚠️  Manual download failed.")
        print("You can try:")
        print("1. Check your internet connection")
        print("2. Run the script again")
        print("3. Use a different ASR model (SherpaWhisperTinyEN)")