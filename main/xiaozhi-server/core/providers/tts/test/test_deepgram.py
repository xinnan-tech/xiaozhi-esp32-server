import sys
import asyncio
from io import BytesIO
import wave
import os
from deepgram import DeepgramClient

if __name__ == "__main__":
    """
    Test for Deepgram TTS
    
    Usage:
        python3 -m core.providers.tts.test_deepgram
        python3 -m core.providers.tts.test_deepgram "Custom text"
    
    Environment:
        DEEPGRAM_API_KEY - Your API key (required)
        DEEPGRAM_MODEL   - Voice model (optional, default: aura-2-thalia-en)
    """

    text = sys.argv[1] if len(sys.argv) > 1 else "Hello, this is a test of Deepgram text to speech."
    
    api_key = os.environ.get("DEEPGRAM_API_KEY")
    if not api_key:
        print("❌ Error: DEEPGRAM_API_KEY not set")
        print("   export DEEPGRAM_API_KEY='your-key'")
        sys.exit(1)
    
    # Get configuration from environment
    model = os.environ.get("DEEPGRAM_MODEL", "aura-2-thalia-en")
    
    print(f"🎙️  Testing Deepgram TTS")
    print(f"   Model: {model}")
    print(f"   Text: {text}\n")
    
    # Create Deepgram client
    client = DeepgramClient(api_key=api_key)
    
    try:
        print("⏳ Generating audio...")
        start = asyncio.get_event_loop().time()
        
        # Generate audio using Deepgram SDK
        audio_stream = client.speak.v1.audio.generate(
            text=text,
            model=model,
            encoding="linear16",  # PCM format
            sample_rate=16000,
            container="none"      # Raw audio
        )
        
        # Collect audio chunks
        audio_bytes = b""
        for chunk in audio_stream:
            audio_bytes += chunk
        
        duration = (asyncio.get_event_loop().time() - start) * 1000
        
        print(f"✅ Audio generated")
        print(f"   Duration: {duration:.0f}ms")
        print(f"   Size: {len(audio_bytes):,} bytes\n")

        # Convert PCM to WAV format
        wav_buffer = BytesIO()
    
        # Open wave file in write mode
        with wave.open(wav_buffer, 'wb') as wf:
            wf.setnchannels(1)       # Mono
            wf.setsampwidth(2)       # 16-bit (2 bytes) per sample
            wf.setframerate(16000)   # Sample rate
            wf.writeframes(audio_bytes) 
        
        # Save to file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_file = os.path.join(script_dir, "tmp", "deepgram_test.wav")
        with open(output_file, 'wb') as f:
            f.write(wav_buffer.getvalue())
        
        print(f"💾 Saved to: {output_file}")
        print("🔊 Playing audio...")
        
        # Play audio file
        os.system(f"afplay '{output_file}'")
        
        print("\n✅ Test completed successfully!")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n👋 Test interrupted")
        sys.exit(1)

