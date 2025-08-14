# SiliconFlow CosyVoice TTS Integration Updates

## Overview
Updated the existing SiliconFlow TTS provider to properly integrate with the CosyVoice API and added 'diana' as the default voice option.

## Changes Made

### 1. Updated TTS Provider (`main/xiaozhi-server/core/providers/tts/siliconflow.py`)

**Key Improvements:**
- ✅ Updated API endpoint to use the correct SiliconFlow URL: `https://api.siliconflow.com/v1/audio/speech`
- ✅ Added proper error handling and logging similar to ElevenLabs implementation
- ✅ Implemented the exact API format you provided with support for:
  - `input`: Text to convert to speech
  - `response_format`: Audio format (mp3, wav, etc.)
  - `stream`: Streaming support (currently set to False)
  - `speed`: Speech speed control
  - `gain`: Audio gain control
  - `model`: CosyVoice model selection
- ✅ Added 'diana' as the default voice
- ✅ Added proper API key validation
- ✅ Added comprehensive error handling for network issues and API errors
- ✅ Added `get_available_voices()` method with supported voices

**Supported Voices:**
- `diana` (Female) - **Default**
- `alex` (Male)
- `bella` (Female)

### 2. Database Migration (`main/manager-api/src/main/resources/db/changelog/202508141200.sql`)

**Changes:**
- ✅ Added 'diana' voice option to the `ai_tts_voice` table
- ✅ Updated default configuration to use 'diana' voice
- ✅ Changed default response format from 'wav' to 'mp3'
- ✅ Added speed and gain parameters to the configuration

### 3. Updated Master Changelog (`db.changelog-master.yaml`)

- ✅ Added the new migration to the changelog sequence

### 4. Test Script (`test_siliconflow_tts.py`)

- ✅ Created a test script to verify the implementation
- ✅ Tests voice generation with diana voice
- ✅ Validates configuration and error handling

## API Configuration

The updated SiliconFlow TTS provider now uses this configuration format:

```json
{
  "type": "siliconflow",
  "model": "FunAudioLLM/CosyVoice2-0.5B",
  "voice": "diana",
  "output_dir": "tmp/",
  "access_token": "YOUR_TOKEN_HERE",
  "response_format": "mp3",
  "speed": 1.0,
  "gain": 0
}
```

## Usage Example

The API request format matches exactly what you provided:

```python
import requests

url = "https://api.siliconflow.com/v1/audio/speech"
payload = {
    "input": "Can you say it with a happy emotion? <|endofprompt|>I'm so happy, Spring Festival is coming!",
    "response_format": "mp3",
    "stream": False,
    "speed": 1,
    "gain": 0,
    "model": "FunAudioLLM/CosyVoice2-0.5B"
}
headers = {
    "Authorization": "Bearer <token>",
    "Content-Type": "application/json"
}

response = requests.post(url, json=payload, headers=headers)
```

## How to Test

1. **Set up your SiliconFlow API token** in the configuration
2. **Run the test script**: `python test_siliconflow_tts.py`
3. **Apply database migration** to add the diana voice option
4. **Configure the system** to use SiliconFlow TTS with diana voice

## Integration with Existing System

The SiliconFlow TTS provider is already registered in the system as `TTS_CosyVoiceSiliconflow`. After applying the database migration, users will be able to:

1. Select SiliconFlow CosyVoice as their TTS provider
2. Choose from available voices including the new 'diana' voice
3. Configure speed, gain, and response format
4. Use the improved error handling and logging

## Next Steps

1. Apply the database migration to add the diana voice
2. Update any existing configurations to use the new diana voice if desired
3. Test the integration with your SiliconFlow API token
4. The system will now default to using 'diana' voice for new SiliconFlow TTS configurations

The implementation maintains full compatibility with the existing system while adding the requested diana voice support and improving the API integration.