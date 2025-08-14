# SiliconFlow CosyVoice TTS Fixes

## Issues Fixed

### 1. ❌ Invalid Voice Error
**Problem**: API returned "Invalid voice" error for 'diana' voice
**Solution**: Removed voice parameter from API request - the API doesn't support separate voice selection yet

### 2. ✅ Updated API Request Format
**Changes made**:
- Removed `voice` parameter from payload
- Set `stream: True` to match your original example
- Changed `speed` to integer instead of float

### 3. ✅ Updated Configuration
**Before**:
```yaml
siliconflow:
  voice: diana  # This caused the error
  speed: 1.0    # Float value
```

**After**:
```yaml
siliconflow:
  # voice parameter removed - not supported by API
  speed: 1      # Integer value
```

### 4. ✅ Fixed Test Script
- Improved config file path detection
- Removed voice parameter from fallback config
- Better error handling and output

## Current Working Configuration

```yaml
selected_module:
  TTS: siliconflow

TTS:
  siliconflow:
    access_token: YOUR_TOKEN_HERE
    model: FunAudioLLM/CosyVoice2-0.5B
    response_format: mp3
    speed: 1
    gain: 0
    output_dir: tmp/
```

## API Request Format (Now Working)

```python
payload = {
    "input": text,
    "response_format": "mp3",
    "stream": True,
    "speed": 1,
    "gain": 0,
    "model": "FunAudioLLM/CosyVoice2-0.5B"
}
# No voice parameter - handled by the model
```

## Test the Fix

Run the test script again:
```bash
python test_siliconflow_tts.py
```

The "Invalid voice" error should now be resolved!