-- Add OpenAI TTS and Gemini TTS providers to dashboard
-- -------------------------------------------------------

-- Add OpenAI TTS provider (only if it doesn't exist)
INSERT IGNORE INTO `ai_model_config` VALUES (
  'TTS_OpenAITTS', 
  'TTS', 
  'OpenAITTS', 
  'OpenAI TTS语音合成', 
  0, 1, 
  '{"type": "openai", "api_key": "你的api_key", "api_url": "https://api.openai.com/v1/audio/speech", "model": "tts-1", "voice": "alloy", "speed": 1.0, "format": "wav", "output_dir": "tmp/"}', 
  NULL, NULL, 16, NULL, NULL, NULL, NULL
);

-- Add Gemini TTS provider (only if it doesn't exist)
INSERT IGNORE INTO `ai_model_config` VALUES (
  'TTS_GeminiTTS', 
  'TTS', 
  'GeminiTTS', 
  'Google Gemini TTS语音合成', 
  0, 1, 
  '{"type": "gemini", "api_key": "你的api_key", "api_url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent", "model": "gemini-2.5-flash-preview-tts", "voice": "Zephyr", "language": "en", "output_dir": "tmp/"}', 
  NULL, NULL, 17, NULL, NULL, NULL, NULL
);
