# SiliconFlow CosyVoice TTS Setup Guide

## Quick Setup

### 1. Get Your SiliconFlow API Token
1. Visit [SiliconFlow](https://siliconflow.com)
2. Sign up or log in to your account
3. Navigate to API settings and generate an API token

### 2. Update Configuration
Edit `main/xiaozhi-server/data/.config.yaml`:

```yaml
selected_module:
  TTS: siliconflow  # ← Change this to use SiliconFlow

TTS:
  siliconflow:
    access_token: YOUR_ACTUAL_TOKEN_HERE  # ← Replace with your token
    model: FunAudioLLM/CosyVoice2-0.5B
    voice: diana  # Default voice (female)
    response_format: mp3
    speed: 1.0
    gain: 0
    output_dir: tmp/
```

### 3. Available Voices
- `diana` - Natural female voice (default) → becomes `FunAudioLLM/CosyVoice2-0.5B:diana`
- `alex` - Male voice → becomes `FunAudioLLM/CosyVoice2-0.5B:alex`
- `bella` - Female voice → becomes `FunAudioLLM/CosyVoice2-0.5B:bella`

**Note**: Voice names are automatically prefixed with the model name when making API requests.

### 4. Test the Setup
Run the test scripts:
```bash
# Test basic functionality
python test_siliconflow_tts.py

# Test fallback functionality
python test_fallback_tts.py
```

## Configuration Options

| Parameter | Description | Default | Options |
|-----------|-------------|---------|---------|
| `access_token` | Your SiliconFlow API token | Required | Your API token |
| `model` | CosyVoice model to use | `FunAudioLLM/CosyVoice2-0.5B` | CosyVoice models |
| `voice` | Voice to use for synthesis | `diana` | `diana`, `alex`, `bella` (auto-prefixed with model) |
| `response_format` | Audio output format | `mp3` | `mp3`, `wav` |
| `speed` | Speech speed | `1.0` | `0.5` to `2.0` |
| `gain` | Audio gain adjustment | `0` | Integer values |
| `output_dir` | Directory for audio files | `tmp/` | Any valid path |
| `fallback.enabled` | Enable ElevenLabs fallback | `true` | `true`, `false` |
| `fallback.elevenlabs.*` | ElevenLabs fallback config | See below | ElevenLabs settings |

### ElevenLabs Fallback Configuration

The system includes automatic fallback to ElevenLabs if SiliconFlow fails:

```yaml
siliconflow:
  # ... SiliconFlow settings ...
  fallback:
    enabled: true
    elevenlabs:
      api_key: YOUR_ELEVENLABS_API_KEY
      voice_id: XJ2fW4ybq7HouelYYGcL  # Rachel voice
      model_id: eleven_turbo_v2_5
      stability: 0.75
      similarity_boost: 0.75
      style: 0.0
      use_speaker_boost: true
      output_format: mp3_44100_128
      optimize_streaming_latency: 0
      output_dir: tmp/
```

## Switching Between TTS Providers

To switch back to other TTS providers, change the `selected_module.TTS` value:

```yaml
selected_module:
  TTS: elevenlabs    # For ElevenLabs
  TTS: kittentts     # For KittenTTS (local)
  TTS: siliconflow   # For SiliconFlow CosyVoice
```

## Troubleshooting

### Common Issues:

1. **"SiliconFlow access token is required"**
   - Make sure you've added your actual API token to the config

2. **"SiliconFlow TTS request failed: 401"**
   - Check that your API token is valid and active

3. **"SiliconFlow TTS request timed out"**
   - Check your internet connection
   - The API might be experiencing high load

4. **Audio file not generated**
   - Ensure the `tmp/` directory exists
   - Check file permissions

### Getting Help:
- Check the SiliconFlow API documentation
- Verify your API token is active
- Test with the provided test script first

## Fallback System Benefits

### 🛡️ **Reliability**
- If SiliconFlow is down or returns errors, automatically switches to ElevenLabs
- Ensures your application continues working even if one service fails
- Transparent fallback - users won't notice the switch

### 🔄 **Automatic Recovery**
- No manual intervention required
- Logs which provider was used for debugging
- Graceful error handling

### ⚡ **Performance**
- Tries fastest/preferred provider first (SiliconFlow)
- Falls back to reliable alternative (ElevenLabs)
- Minimal latency impact

## Example Usage

Once configured, the system will:
1. **First**: Try SiliconFlow CosyVoice with diana voice
2. **If SiliconFlow fails**: Automatically use ElevenLabs with Rachel voice
3. **Log the process**: For monitoring and debugging

The fallback is completely transparent to your application.