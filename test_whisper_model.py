#!/usr/bin/env python3
"""
Test script to verify Whisper model initialization
"""

import sys
import os
sys.path.append('main/xiaozhi-server')

def test_whisper_initialization():
    """Test Whisper model initialization with correct parameters"""
    try:
        import sherpa_onnx
        
        # Test the exact parameters we're using
        model_dir = "models/sherpa-onnx-whisper-tiny.en"
        
        # Check if model files exist
        encoder_path = os.path.join(model_dir, "tiny.en-encoder.onnx")
        decoder_path = os.path.join(model_dir, "tiny.en-decoder.onnx")
        tokens_path = os.path.join(model_dir, "tiny.en-tokens.txt")
        
        print("Checking model files...")
        print(f"Encoder exists: {os.path.exists(encoder_path)}")
        print(f"Decoder exists: {os.path.exists(decoder_path)}")
        print(f"Tokens exists: {os.path.exists(tokens_path)}")
        
        if all(os.path.exists(p) for p in [encoder_path, decoder_path, tokens_path]):
            print("\n✅ All model files found!")
            
            print("Testing Whisper model initialization...")
            model = sherpa_onnx.OfflineRecognizer.from_whisper(
                encoder=encoder_path,
                decoder=decoder_path,
                tokens=tokens_path,
                num_threads=2,
                decoding_method="greedy_search",
                debug=False,
            )
            print("✅ Whisper model initialized successfully!")
            return True
        else:
            print("❌ Model files not found. Please run the server first to download them.")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("Testing Whisper Tiny English model initialization...")
    success = test_whisper_initialization()
    
    if success:
        print("\n🎉 Your Whisper model is ready!")
        print("The server should start successfully now.")
    else:
        print("\n⚠️  There might be an issue with the model setup.")
        print("Try running the server to download the model files first.")