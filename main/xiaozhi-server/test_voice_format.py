#!/usr/bin/env python3
"""
Test script to verify voice format handling
"""

import sys
import os

# Add the main directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'main', 'xiaozhi-server'))

from core.providers.tts.siliconflow import TTSProvider

def test_voice_format():
    """Test that voice names are correctly formatted with model prefix"""
    
    # Test configurations
    test_configs = [
        {
            "access_token": "test_token",
            "model": "FunAudioLLM/CosyVoice2-0.5B",
            "voice": "diana",  # Should become FunAudioLLM/CosyVoice2-0.5B:diana
        },
        {
            "access_token": "test_token", 
            "model": "FunAudioLLM/CosyVoice2-0.5B",
            "voice": "FunAudioLLM/CosyVoice2-0.5B:alex",  # Should stay as is
        },
        {
            "access_token": "test_token",
            "model": "FunAudioLLM/CosyVoice2-0.5B",
            # No voice specified - should default to diana with prefix
        }
    ]
    
    for i, config in enumerate(test_configs):
        try:
            provider = TTSProvider(config, delete_audio_file=True)
            print(f"Test {i+1}:")
            print(f"  Input voice: {config.get('voice', 'None (default)')}")
            print(f"  Final voice: {provider.voice}")
            print(f"  Model: {provider.model}")
            
            # Test available voices
            voices = provider.get_available_voices()
            print(f"  Available voices: {voices}")
            print()
            
        except Exception as e:
            print(f"Test {i+1} failed: {e}")
            print()

if __name__ == "__main__":
    print("Testing SiliconFlow voice format handling...")
    test_voice_format()