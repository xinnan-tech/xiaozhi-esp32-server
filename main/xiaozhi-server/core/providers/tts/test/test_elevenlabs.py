import sys
import asyncio
from io import BytesIO
import wave
import os
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings

if __name__ == "__main__":
    """
    Test for ElevenLabs TTS
    
    Usage:
        python3 -m core.providers.tts.elevenlabs
        python3 -m core.providers.tts.elevenlabs "Custom text"
    
    Environment:
        ELEVENLABS_API_KEY - Your API key (required)
        ELEVENLABS_VOICE_ID - Voice ID (optional)
    """

    text = sys.argv[1] if len(sys.argv) > 1 else "Hello, this is a test of ElevenLabs text to speech."
    
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        print("❌ Error: ELEVENLABS_API_KEY not set")
        print("   export ELEVENLABS_API_KEY='your-key'")
        sys.exit(1)
    
    # Create minimal provider instance
    client = ElevenLabs(api_key=api_key)
    voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")
    voice_settings = VoiceSettings(
        stability=0.5,
        similarity_boost=0.75,
        style=0.0,
        use_speaker_boost=True
    )
    
    try:
        
        print("⏳ Generating audio...")
        start = asyncio.get_event_loop().time()
        
        # Generate audio
        audio_stream = client.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
            model_id="eleven_multilingual_v2",
            output_format="pcm_16000",
            voice_settings=voice_settings
        )
        
        # Collect chunks
        audio_bytes = b''.join(chunk for chunk in audio_stream if chunk)
        duration = (asyncio.get_event_loop().time() - start) * 1000
        
        print(f"✅ Audio generated")
        print(f"   Duration: {duration:.0f}ms")
        print(f"   Size: {len(audio_bytes):,} bytes\n")

        # Convert to WAV format
        wav_buffer = BytesIO()
    
        # Open wave file in write mode
        with wave.open(wav_buffer, 'wb') as wf:
            wf.setnchannels(1)           # Mono or stereo
            wf.setsampwidth(2)       # 16-bit (2 bytes) per sample
            wf.setframerate(16000)        # Sample rate (e.g., 16000 Hz)
            wf.writeframes(audio_bytes) 
        wav_buffer.getvalue()

        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_file = os.path.join(script_dir, "tmp", "elevenlabs_test.wav")

        with open(output_file, 'wb') as f:
            f.write(wav_buffer.getvalue())
        # here，I want to get a .wav file to play the audio file
        os.system(f"afplay '{output_file}'")

    except KeyboardInterrupt:
        print("\n\n👋 Test interrupted")
        sys.exit(1)