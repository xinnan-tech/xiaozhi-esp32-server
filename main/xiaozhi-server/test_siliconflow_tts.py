#!/usr/bin/env python3
"""
Test script for SiliconFlow CosyVoice TTS Provider
"""

import sys
import os
import asyncio
import yaml

# Add the main directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'main', 'xiaozhi-server'))

from core.providers.tts.siliconflow import TTSProvider

def load_config():
    """Load configuration from .config.yaml"""
    # Try different possible paths
    possible_paths = [
        os.path.join(os.path.dirname(__file__), 'data', '.config.yaml'),
        os.path.join(os.path.dirname(__file__), 'main', 'xiaozhi-server', 'data', '.config.yaml'),
        'data/.config.yaml'
    ]
    
    for config_path in possible_paths:
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            print(f"✅ Loaded config from: {config_path}")
            return config.get('TTS', {}).get('siliconflow', {})
        except Exception:
            continue
    
    print("Warning: Could not load config from any expected location")
    return {}

async def test_siliconflow_tts():
    """Test SiliconFlow TTS with diana voice"""
    
    # Load configuration from .config.yaml
    config = load_config()
    
    # Fallback configuration if config file not found
    if not config:
        config = {
            "model": "FunAudioLLM/CosyVoice2-0.5B",
            "access_token": "sk-kuyamprtzyvtetbnsyoysbbxuwqzyraldecobjetvdeowzte",  # Replace with actual token
            "response_format": "mp3",
            "speed": 1,
            "gain": 0,
            "output_dir": "tmp/"
        }
    
    try:
        # Initialize TTS provider
        tts_provider = TTSProvider(config, delete_audio_file=False)
        
        # Test text
        test_text = "Hello, this is a test of SiliconFlow CosyVoice TTS with Diana voice."
        
        # Generate speech
        output_file = "test_diana_voice.mp3"
        print(f"Generating speech for: {test_text}")
        print(f"Using voice: {tts_provider.voice or 'Default (model-based)'}")
        print(f"Using model: {tts_provider.model}")
        
        await tts_provider.text_to_speak(test_text, output_file)
        
        if os.path.exists(output_file):
            print(f"✅ Success! Audio file generated: {output_file}")
            print(f"File size: {os.path.getsize(output_file)} bytes")
        else:
            print("❌ Failed to generate audio file")
            
        # Test available voices
        voices = tts_provider.get_available_voices()
        print(f"\nAvailable voices: {voices}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("Testing SiliconFlow CosyVoice TTS Provider...")
    print("Note: You need to set a valid SiliconFlow access token in the config")
    asyncio.run(test_siliconflow_tts())