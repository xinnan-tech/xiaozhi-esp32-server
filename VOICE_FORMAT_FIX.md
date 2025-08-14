# SiliconFlow Voice Format Fix

## Issue
SiliconFlow CosyVoice API requires system-predefined voices to be prefixed with the model name in the format:
```
FunAudioLLM/CosyVoice2-0.5B:alex
```

## Solution Implemented

### 1. **Updated TTS Provider Logic**
The `siliconflow.py` provider now automatically handles voice formatting:

```python
# Voice configuration - default to diana with model prefix
if config.get("private_voice"):
    self.voice = config.get("private_voice")
else:
    voice_name = config.get("voice", "diana")
    # If voice doesn't already contain model prefix, add it
    if ":" not in voice_name:
        self.voice = f"{self.model}:{voice_name}"
    else:
        self.voice = voice_name
```

### 2. **Voice Parameter in API Request**
The voice parameter is now properly included in the API payload:

```python
# Add voice parameter with model prefix (e.g., FunAudioLLM/CosyVoice2-0.5B:diana)
if self.voice:
    payload["voice"] = self.voice
```

### 3. **Updated Available Voices**
The `get_available_voices()` method now returns properly formatted voice names:

```python
def get_available_voices(self):
    model_prefix = self.model
    return [
        (f"{model_prefix}:diana", "Diana (Female)"),
        (f"{model_prefix}:alex", "Alex (Male)"),
        (f"{model_prefix}:bella", "Bella (Female)"),
    ]
```

## Configuration Examples

### Simple Configuration (Recommended)
```yaml
siliconflow:
  model: FunAudioLLM/CosyVoice2-0.5B
  voice: diana  # Automatically becomes FunAudioLLM/CosyVoice2-0.5B:diana
```

### Full Format Configuration
```yaml
siliconflow:
  model: FunAudioLLM/CosyVoice2-0.5B
  voice: FunAudioLLM/CosyVoice2-0.5B:alex  # Used as-is
```

## API Request Format
The final API request will look like:

```json
{
  "input": "Hello world",
  "response_format": "mp3",
  "stream": true,
  "speed": 1.0,
  "gain": 0,
  "model": "FunAudioLLM/CosyVoice2-0.5B",
  "voice": "FunAudioLLM/CosyVoice2-0.5B:diana"
}
```

## Benefits
1. **User-Friendly**: Users can specify just the voice name (`diana`, `alex`, `bella`)
2. **Flexible**: Supports both simple names and full format
3. **Automatic**: Model prefix is added automatically
4. **Backward Compatible**: Existing full-format configurations still work

## Testing
Use `test_voice_format.py` to verify the voice formatting logic works correctly.

The system now properly handles the SiliconFlow voice format requirement while maintaining ease of use for configuration.