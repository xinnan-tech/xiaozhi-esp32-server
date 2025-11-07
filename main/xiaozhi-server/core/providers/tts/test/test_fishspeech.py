import sys
import os
from io import BytesIO
import wave
import platform
from fish_audio_sdk import Session, TTSRequest
import asyncio

if __name__ == "__main__":
    """
    Test for FishSpeech TTS
    
    Usage:
        python3 -m core.providers.tts.test.test_fishspeech
        python3 -m core.providers.tts.test.test_fishspeech "Custom text"
    
    Environment:
        FISH_API_KEY - Your Fish.Audio API key (required)
        FISH_REFERENCE_ID - Voice reference ID (optional)
    
    Examples:
        export FISH_API_KEY="your-key"
        python3 -m core.providers.tts.test.test_fishspeech "Hello world"
        
        # With custom voice
        export FISH_REFERENCE_ID="7f92f8afb8ec43bf81429cc1c9199cb1"
        python3 -m core.providers.tts.test.test_fishspeech "Hello world"
    """

    text = sys.argv[1] if len(sys.argv) > 1 else "Hello, this is a test of FishSpeech text to speech."
    
    api_key = os.environ.get("FISH_API_KEY")
    if not api_key:
        print("❌ Error: FISH_API_KEY not set")
        print("   export FISH_API_KEY='your-key'")
        print("\n💡 Get your API key from: https://fish.audio/")
        sys.exit(1)
    
    # default reference id is Donald Trump
    reference_id = os.environ.get("FISH_REFERENCE_ID", "5196af35f6ff4a0dbf541793fc9f2157")
    
    print(f"🐟 FishSpeech TTS Test")
    print(f"   API: https://api.fish.audio")
    if reference_id:
        print(f"   Reference ID: {reference_id}")
    print(f"   Text: {text[:50]}{'...' if len(text) > 50 else ''}\n")
    
    try:
        print("⏳ Generating audio...")
        start = asyncio.get_event_loop().time()
        
        # Create session
        session = Session(api_key)
        
        # Prepare TTS request
        tts_request = TTSRequest(
            text=text,
            reference_id=reference_id,
            format="pcm",
            normalize=True,
            sample_rate=16000,
        )
        
        # Generate audio
        audio_stream = session.tts(tts_request, backend="s1")
        duration = (asyncio.get_event_loop().time() - start) * 1000

        audio_bytes = b''.join(chunk for chunk in audio_stream if chunk)
        
        print(f"✅ Audio generated")
        print(f"   Duration: {duration:.0f}ms")

        # Convert to WAV format
        wav_buffer = BytesIO()
    
        # Open wave file in write mode
        with wave.open(wav_buffer, 'wb') as wf:
            wf.setnchannels(1)           # Mono or stereo
            wf.setsampwidth(2)       # 16-bit (2 bytes) per sample
            wf.setframerate(16000)        # Sample rate (e.g., 16000 Hz)
            wf.writeframes(audio_bytes) 
        
        # Save to file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_file = os.path.join(script_dir, "tmp", "fish_test.wav")
        
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'wb') as f:
            f.write(wav_buffer.getvalue())
        
        os.system(f"afplay '{output_file}'")
        
        print("\n✅ Test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n👋 Test interrupted")
        sys.exit(1)
