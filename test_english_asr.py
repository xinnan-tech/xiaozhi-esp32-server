#!/usr/bin/env python3
"""
Test script for English-only Sherpa-ONNX ASR models
Usage: python test_english_asr.py
"""

import sys
import os
sys.path.append('main/xiaozhi-server')

from core.providers.asr.sherpa_onnx_local import ASRProvider

def test_english_models():
    """Test different English-only Sherpa-ONNX models"""
    
    models_to_test = [
        {
            "name": "Whisper Tiny English (Smallest)",
            "config": {
                "model_dir": "models/sherpa-onnx-whisper-tiny.en",
                "model_type": "whisper",
                "output_dir": "tmp/"
            }
        },
        {
            "name": "Whisper Base English (Good Balance)", 
            "config": {
                "model_dir": "models/sherpa-onnx-whisper-base.en",
                "model_type": "whisper",
                "output_dir": "tmp/"
            }
        },
        {
            "name": "Zipformer English (RECOMMENDED - Verified Working)",
            "config": {
                "model_dir": "models/sherpa-onnx-zipformer-en-2023-04-01",
                "model_type": "zipformer",
                "output_dir": "tmp/"
            }
        },
        {
            "name": "Zipformer Gigaspeech English (Large Vocabulary)",
            "config": {
                "model_dir": "models/sherpa-onnx-zipformer-gigaspeech-2023-12-12",
                "model_type": "zipformer",
                "output_dir": "tmp/"
            }
        },
        {
            "name": "Paraformer English (Alternative Architecture)",
            "config": {
                "model_dir": "models/sherpa-onnx-paraformer-en-2023-10-24",
                "model_type": "paraformer",
                "output_dir": "tmp/"
            }
        }
    ]
    
    for model_info in models_to_test:
        print(f"\n=== Testing {model_info['name']} ===")
        try:
            asr = ASRProvider(model_info['config'], delete_audio_file=False)
            print(f"✅ {model_info['name']} initialized successfully")
            print(f"   Model directory: {model_info['config']['model_dir']}")
            print(f"   Model type: {model_info['config']['model_type']}")
        except Exception as e:
            print(f"❌ {model_info['name']} failed to initialize: {e}")

if __name__ == "__main__":
    print("Testing English-only Sherpa-ONNX ASR models...")
    test_english_models()
    print("\nTest completed!")