import sys
import asyncio
from io import BytesIO
import wave
import os
import cartesia

if __name__ == "__main__":
    """
    Test for Cartesia TTS
    
    Usage:
        python3 -m core.providers.tts.test_cartesia
        python3 -m core.providers.tts.test_cartesia "Custom text"
    
    Environment:
        CARTESIA_API_KEY - Your API key (required)
        CARTESIA_VOICE_ID - Voice ID (optional, default: a0e99841-438c-4a64-b679-ae501e7d6091)
        CARTESIA_MODEL - Model (optional, default: sonic-english)
    """

    text = sys.argv[1] if len(sys.argv) > 1 else "Hello, this is a test of Cartesia text to speech."
    
    api_key = os.environ.get("CARTESIA_API_KEY")
    if not api_key:
        print("❌ Error: CARTESIA_API_KEY not set")
        print("   export CARTESIA_API_KEY='your-key'")
        sys.exit(1)
    
    # Get configuration from environment
    voice_id = os.environ.get("CARTESIA_VOICE_ID", "f9a4b3a6-b44b-469f-90e3-c8e19bd30e99")
    model = os.environ.get("CARTESIA_MODEL", "sonic-3")
    
    print(f"🎙️  Testing Cartesia TTS")
    print(f"   Model: {model}")
    print(f"   Voice ID: {voice_id[:16]}...")
    print(f"   Text: {text}\n")
    
    # Create Cartesia client
    client = cartesia.Cartesia(api_key=api_key)
    
    try:
        print("⏳ Generating audio...")
        start = asyncio.get_event_loop().time()
        
        # Create WebSocket connection
        ws = client.tts.websocket()
        
        # Collect audio chunks
        pcm_chunks = []
        
        # Send request and receive audio stream
        for output in ws.send(
            model_id=model,
            transcript=text,
            voice={
                "mode": "id",
                "id": voice_id
            },
            stream=True,
            output_format={
                "container": "raw",
                "encoding": "pcm_s16le",  # 16-bit PCM
                "sample_rate": 16000
            },
            language="zh"
        ):
            # Collect PCM audio data
            if output and hasattr(output, 'audio') and output.audio:
                pcm_chunks.append(output.audio)
        
        # Merge all PCM chunks
        audio_bytes = b''.join(pcm_chunks)
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
        output_file = os.path.join(script_dir, "tmp", "cartesia_test.wav")
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

