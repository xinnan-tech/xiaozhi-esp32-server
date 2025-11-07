import sys
import asyncio
import json
from io import BytesIO
import wave
import os
import platform
import aiohttp

if __name__ == "__main__":
    """
    Test for Minimax TTS
    
    Usage:
        python3 -m core.providers.tts.test.test_minimax
        python3 -m core.providers.tts.test.test_minimax "Custom text"
    
    Environment:
        MINIMAX_API_KEY - Your API key (required)
        MINIMAX_GROUP_ID - Your Group ID (required)
        MINIMAX_MODEL - Model name (optional, default: speech-01-turbo)
        MINIMAX_VOICE_ID - Voice ID (optional, default: female-shaonv)
    """

    text = sys.argv[1] if len(sys.argv) > 1 else "Hello, this is a test of Minimax text to speech."
    
    # Check required environment variables
    api_key = os.environ.get("MINIMAX_API_KEY")
    group_id = os.environ.get("MINIMAX_GROUP_ID")
    
    if not api_key:
        print("❌ Error: MINIMAX_API_KEY not set")
        print("   export MINIMAX_API_KEY='your-key'")
        sys.exit(1)
    
    if not group_id:
        print("❌ Error: MINIMAX_GROUP_ID not set")
        print("   export MINIMAX_GROUP_ID='your-group-id'")
        sys.exit(1)
    
    # Optional parameters
    model = os.environ.get("MINIMAX_MODEL", "speech-2.6-hd")
    voice_id = os.environ.get("MINIMAX_VOICE_ID", "English_Graceful_Lady")
    
    # Configuration
    host = "api.minimax.io"
    api_url = f"https://{host}/v1/t2a_v2"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    
    payload = {
        "model": model,
        "text": text,
        "stream": True,
        "voice_setting": {
            "voice_id": voice_id,
            "speed": 1.0,
            "vol": 1.0,
            "pitch": 0,
            "emotion": "happy",
        },
        "pronunciation_dict": {
            "tone": []
        },
        "audio_setting": {
            "sample_rate": 16000,
            "format": "pcm",
            "channel": 1,
        }
    }
    
    async def test():
        try:
            print(f"⏳ Generating audio with Minimax TTS...")
            print(f"   Model: {model}")
            print(f"   Voice: {voice_id}")
            print(f"   Text: {text[:50]}{'...' if len(text) > 50 else ''}\n")
            
            start_time = asyncio.get_event_loop().time()
            pcm_chunks = []
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    api_url,
                    headers=headers,
                    data=json.dumps(payload),
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    
                    if resp.status != 200:
                        error_text = await resp.text()
                        print(f"❌ API Error: {resp.status}")
                        print(f"   Response: {error_text}")
                        sys.exit(1)
                    
                    # Process streaming audio data
                    buffer = b""
                    async for chunk in resp.content.iter_any():
                        if not chunk:
                            continue
                        
                        buffer += chunk
                        
                        # Parse SSE (Server-Sent Events) format
                        while True:
                            # Find data chunk separator
                            header_pos = buffer.find(b"data: ")
                            if header_pos == -1:
                                break
                            
                            end_pos = buffer.find(b"\n\n", header_pos)
                            if end_pos == -1:
                                break
                            
                            # Extract single complete JSON block
                            json_str = buffer[header_pos + 6 : end_pos].decode("utf-8")
                            buffer = buffer[end_pos + 2 :]
                            
                            try:
                                data = json.loads(json_str)
                                status = data.get("data", {}).get("status", 1)
                                audio_hex = data.get("data", {}).get("audio")
                                
                                # Only process status=1 valid audio chunks
                                # Ignore status=2 end summary chunks
                                if status == 1 and audio_hex:
                                    # Decode hex string to PCM bytes
                                    audio_bytes = bytes.fromhex(audio_hex)
                                    pcm_chunks.append(audio_bytes)
                                elif status == 2:
                                    # End of stream
                                    break
                            except json.JSONDecodeError as e:
                                print(f"⚠️  Warning: Failed to parse JSON: {e}")
                                continue
            
            duration = (asyncio.get_event_loop().time() - start_time) * 1000
            
            # Combine all PCM chunks
            pcm_data = b''.join(pcm_chunks)
            
            if not pcm_data:
                print("❌ Error: No audio data received")
                sys.exit(1)
            
            print(f"✅ Audio generated")
            print(f"   Duration: {duration:.0f}ms")
            print(f"   Size: {len(pcm_data):,} bytes")
            print(f"   Chunks: {len(pcm_chunks)}\n")
            
            # Convert PCM to WAV format
            wav_buffer = BytesIO()
            with wave.open(wav_buffer, 'wb') as wf:
                wf.setnchannels(1)           # Mono
                wf.setsampwidth(2)           # 16-bit (2 bytes) per sample
                wf.setframerate(24000)       # Sample rate: 24000 Hz
                wf.writeframes(pcm_data)
            
            # Save to file
            script_dir = os.path.dirname(os.path.abspath(__file__))
            output_file = os.path.join(script_dir, "tmp", "minimax_test.wav")
            
            # Create tmp directory if not exists
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            with open(output_file, 'wb') as f:
                f.write(wav_buffer.getvalue())
            
            print(f"💾 Saved to: {output_file}\n")
            print("🔊 Playing audio...")
            
            # Play audio (platform-specific)
            system = platform.system()
            if system == "Darwin":  # macOS
                os.system(f"afplay '{output_file}'")
            elif system == "Linux":
                # Try common Linux audio players
                if os.system("which aplay > /dev/null 2>&1") == 0:
                    os.system(f"aplay '{output_file}'")
                elif os.system("which ffplay > /dev/null 2>&1") == 0:
                    os.system(f"ffplay -nodisp -autoexit '{output_file}' 2>/dev/null")
                else:
                    print("⚠️  No audio player found (aplay/ffplay)")
            elif system == "Windows":
                os.system(f'start {output_file}')
            else:
                print(f"⚠️  Unsupported platform: {system}")
            
            print("\n✅ Test completed successfully!")
        
        except aiohttp.ClientError as e:
            print(f"❌ Network error: {e}")
            sys.exit(1)
        except KeyboardInterrupt:
            print("\n\n👋 Test interrupted")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    # Run the async test
    asyncio.run(test())

