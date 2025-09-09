-- Add EdgeTTS Ana voice (en-US-AnaNeural) for default agent configuration
delete from `ai_tts_voice` where id = 'TTS_EdgeTTS_Ana';
INSERT INTO `ai_tts_voice` VALUES ('TTS_EdgeTTS_Ana', 'TTS_EdgeTTS', 'EdgeTTS Ana', 'en-US-AnaNeural', 'English', NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL);