"""
Groq ASR (Whisper) Test

This script tests Groq's speech-to-text API using the OpenAI SDK.
Groq is compatible with OpenAI's API format.

Usage:
    # Record and transcribe
    python3 -m core.providers.asr.test.test_groq
    
    # Transcribe existing audio file
    python3 -m core.providers.asr.test.test_groq path/to/audio.wav

Environment:
    GROQ_API_KEY - Your Groq API key (required)

Examples:
    export GROQ_API_KEY="gsk_your_key_here"
    python3 -m core.providers.asr.test.test_groq
    python3 -m core.providers.asr.test.test_groq /path/to/test.wav
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


def test_groq_asr(audio_file_path: str):
    """
    Test Groq ASR with the given audio file
    
    Args:
        audio_file_path: Path to the audio WAV file
        api_key: Groq API key
        model: Groq Whisper model name (default: whisper-large-v3)
        
    Returns:
        Tuple of (transcribed_text, latency_ms)
    """
    print(f"🤖 Groq ASR Test")
    print(f"   API: https://api.groq.com/openai/v1")
    model = "whisper-large-v3"
    api_key = os.environ.get("GROQ_API_KEY")
    print(f"   Model: {model}")
    print(f"   Audio: {audio_file_path}")
    
    # Get file size
    file_size = os.path.getsize(audio_file_path) / 1024  # KB
    print(f"   Size: {file_size:.1f} KB\n")
    
    # Initialize OpenAI client with Groq endpoint
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1"
    )
    
    try:
        print("⏳ Transcribing audio...")
        start_time = time.time()
        
        # Open audio file and send to Groq
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
        
        # Test Groq ASR
        text, latency = test_groq_asr(audio_path)
        
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

