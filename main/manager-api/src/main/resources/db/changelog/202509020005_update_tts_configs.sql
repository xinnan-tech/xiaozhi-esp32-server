-- Update existing TTS configurations with proper API keys and model codes
-- This replaces the modified 202509020001 changeset to avoid checksum issues
-- -----------------------------------------------------------------------

-- Update OpenAI TTS configuration with proper API key and model code
UPDATE `ai_model_config` SET 
  `model_code` = 'openai',
  `config_json` = '{"type": "openai", "api_key": "YOUR_OPENAI_API_KEY", "api_url": "https://api.openai.com/v1/audio/speech", "model": "tts-1", "voice": "alloy", "speed": 1.0, "output_dir": "tmp/"}'
WHERE `id` = 'TTS_OpenAITTS';

-- Update Gemini TTS configuration with proper API key and model code  
UPDATE `ai_model_config` SET 
  `model_code` = 'gemini',
  `config_json` = '{"type": "gemini", "api_key": "YOUR_GEMINI_API_KEY", "api_url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent", "model": "gemini-2.5-flash-preview-tts", "voice": "Zephyr", "language": "en", "output_dir": "tmp/"}'
WHERE `id` = 'TTS_GeminiTTS';