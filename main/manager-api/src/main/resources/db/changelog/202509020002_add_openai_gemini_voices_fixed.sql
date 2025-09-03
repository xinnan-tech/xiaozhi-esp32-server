-- Add voice options for OpenAI TTS and Gemini TTS providers
-- -------------------------------------------------------

-- OpenAI TTS Voices (only if they don't exist)
INSERT IGNORE INTO `ai_tts_voice` VALUES 
('TTS_OpenAI0001', 'TTS_OpenAITTS', 'Alloy - Neutral', 'alloy', 'English', NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL),
('TTS_OpenAI0002', 'TTS_OpenAITTS', 'Echo - Male', 'echo', 'English', NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL),
('TTS_OpenAI0003', 'TTS_OpenAITTS', 'Fable - British', 'fable', 'English', NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL),
('TTS_OpenAI0004', 'TTS_OpenAITTS', 'Onyx - Deep Male', 'onyx', 'English', NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL),
('TTS_OpenAI0005', 'TTS_OpenAITTS', 'Nova - Female', 'nova', 'English', NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL),
('TTS_OpenAI0006', 'TTS_OpenAITTS', 'Shimmer - Soft Female', 'shimmer', 'English', NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL);

-- Gemini TTS Voices (only if they don't exist)
INSERT IGNORE INTO `ai_tts_voice` VALUES 
('TTS_Gemini0001', 'TTS_GeminiTTS', 'Zephyr - Bright', 'Zephyr', 'English', NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL),
('TTS_Gemini0002', 'TTS_GeminiTTS', 'Puck - Upbeat', 'Puck', 'English', NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL),
('TTS_Gemini0003', 'TTS_GeminiTTS', 'Charon - Deep', 'Charon', 'English', NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL),
('TTS_Gemini0004', 'TTS_GeminiTTS', 'Kore - Warm', 'Kore', 'English', NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL),
('TTS_Gemini0005', 'TTS_GeminiTTS', 'Fenrir - Strong', 'Fenrir', 'English', NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL),
('TTS_Gemini0006', 'TTS_GeminiTTS', 'Aoede - Musical', 'Aoede', 'English', NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL);
