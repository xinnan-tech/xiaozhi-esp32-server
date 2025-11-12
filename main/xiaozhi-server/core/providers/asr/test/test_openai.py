"""
OpenAI ASR (Whisper) Test

This script tests OpenAI's official Whisper speech-to-text API.

Usage:
    # Record and transcribe
    python3 -m core.providers.asr.test.test_openai
    
    # Transcribe existing audio file
    python3 -m core.providers.asr.test.test_openai path/to/audio.wav

Environment:
    OPENAI_API_KEY - Your OpenAI API key (required)

Examples:
    export OPENAI_API_KEY="sk-proj-your_key_here"
    python3 -m core.providers.asr.test.test_openai
    python3 -m core.providers.asr.test.test_openai /path/to/test.wav
"""

import sys
import os
import time
import platform

# Check if OpenAI SDK is installed
try:
    from openai import OpenAI
except ImportError:
    print("❌ Error: openai package not installed")
    print("   Install with: pip install openai")
    sys.exit(1)

# Import audio recorder
try:
    from core.providers.asr.test.audio_recorder import record_audio_file
except ImportError:
    print("❌ Error: Could not import audio_recorder")
    print("   Make sure you're running from xiaozhi-server directory")
    sys.exit(1)


def test_openai_asr(audio_file_path: str):
    """
    Test OpenAI Whisper ASR with the given audio file
    
    Args:
        audio_file_path: Path to the audio WAV file
        
    Returns:
        Tuple of (transcribed_text, latency_ms)
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("❌ Error: OPENAI_API_KEY not set")
        print("   export OPENAI_API_KEY='sk-proj-your_key_here'")
        print("\n💡 Get your API key from: https://platform.openai.com/api-keys")
        sys.exit(1)
    
    # model = "whisper-1" # transcription performance is low
    model = "gpt-4o-transcribe"
    
    print(f"🤖 OpenAI ASR Test")
    print(f"   API: https://api.openai.com/v1")
    print(f"   Model: {model}")
    print(f"   Audio: {audio_file_path}")
    
    # Get file size
    file_size = os.path.getsize(audio_file_path) / 1024  # KB
    print(f"   Size: {file_size:.1f} KB\n")
    
    # Initialize OpenAI client
    client = OpenAI(api_key=api_key)
    
    try:
        print("⏳ Transcribing audio...")
        start_time = time.time()
        
        # Open audio file and send to OpenAI
        with open(audio_file_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model=model,
                file=audio_file,
                response_format="text"
            )
        
        end_time = time.time()
        latency_ms = (end_time - start_time) * 1000
        
        # Get transcription text
        if isinstance(transcription, str):
            text = transcription
        else:
            text = transcription.text if hasattr(transcription, 'text') else str(transcription)
        
        return text, latency_ms
        
    except Exception as e:
        print(f"❌ Transcription failed: {e}")
        raise


if __name__ == "__main__":
    try:
        # Check if audio file path is provided as argument
        if len(sys.argv) > 1:
            audio_path = sys.argv[1]
            if not os.path.exists(audio_path):
                print(f"❌ Error: Audio file not found: {audio_path}")
                sys.exit(1)
            print(f"📂 Using provided audio file: {audio_path}\n")
        else:
            # Record audio
            audio_path = record_audio_file()
        
        # Test OpenAI ASR
        text, latency = test_openai_asr(audio_path)
        
        # Print results
        print("=" * 60)
        print("✅ Transcription Result:")
        print("=" * 60)
        print(f"\n{text}\n")
        print("=" * 60)
        print(f"⏱️  Latency: {latency:.0f} ms ({latency/1000:.2f}s)")
        print("=" * 60)
        
        # Play audio on macOS if it was just recorded
        if len(sys.argv) == 1 and platform.system() == "Darwin":
            print("\n🔊 Playing back audio...")
            os.system(f"afplay '{audio_path}'")
        
        print("\n✅ Test completed successfully!")
        
    except KeyboardInterrupt:
        print("\n\n👋 Test interrupted")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

