#!/usr/bin/env python3
"""
Test script for SiliconFlow TTS with ElevenLabs fallback
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
    config_path = os.path.join(os.path.dirname(__file__), 'main', 'xiaozhi-server', 'data', '.config.yaml')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config.get('TTS', {}).get('siliconflow', {})
    except Exception as e:
        print(f"Warning: Could not load config from {config_path}: {e}")
        return {}

async def test_fallback_functionality():
    """Test SiliconFlow TTS with ElevenLabs fallback"""
    
    # Load configuration from .config.yaml
    config = load_config()
    
    if not config:
        print("❌ Could not load SiliconFlow configuration")
        return
    
    print("✅ Loaded SiliconFlow configuration with fallback")
    print(f"Primary: SiliconFlow CosyVoice ({config.get('model', 'N/A')})")
    print(f"Fallback: {'Enabled' if config.get('fallback', {}).get('enabled') else 'Disabled'}")
    
    try:
        # Initialize TTS provider with fallback
        tts_provider = TTSProvider(config, delete_audio_file=False)
        
        # Test text
        test_text = "Testing SiliconFlow with ElevenLabs fallback functionality."
        
        print(f"\n🔄 Testing with text: {test_text}")
        print(f"Primary voice: {tts_provider.voice}")
        print(f"Fallback available: {'Yes' if tts_provider.fallback_provider else 'No'}")
        
        # Generate speech (this will try SiliconFlow first, then ElevenLabs if it fails)
        output_file = "test_fallback_tts.mp3"
        
        print(f"\n🎯 Attempting TTS generation...")
        await tts_provider.text_to_speak(test_text, output_file)
        
        if os.path.exists(output_file):
            print(f"✅ Success! Audio file generated: {output_file}")
            print(f"File size: {os.path.getsize(output_file)} bytes")
        else:
            print("❌ Failed to generate audio file")
            
    except Exception as e:
        print(f"❌ Error: {e}")

async def test_forced_fallback():
    """Test fallback by using invalid SiliconFlow token"""
    
    config = load_config()
    if not config:
        return
    
    # Force fallback by using invalid token
    config['access_token'] = 'invalid_token_to_force_fallback'
    
    print(f"\n🔄 Testing forced fallback (invalid SiliconFlow token)...")
    
    try:
        tts_provider = TTSProvider(config, delete_audio_file=False)
        
        test_text = "This should use ElevenLabs fallback due to invalid SiliconFlow token."
        output_file = "test_forced_fallback.mp3"
        
        await tts_provider.text_to_speak(test_text, output_file)
        
        if os.path.exists(output_file):
            print(f"✅ Fallback successful! Audio file generated: {output_file}")
            print(f"File size: {os.path.getsize(output_file)} bytes")
        else:
            print("❌ Fallback failed")
            
    except Exception as e:
        print(f"❌ Both providers failed: {e}")

if __name__ == "__main__":
    print("Testing SiliconFlow TTS with ElevenLabs Fallback...")
    print("=" * 60)
    
    asyncio.run(test_fallback_functionality())
    asyncio.run(test_forced_fallback())