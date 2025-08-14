-- Add diana voice for SiliconFlow CosyVoice TTS
INSERT INTO `ai_tts_voice` VALUES ('TTS_CosyVoiceSiliconflow0003', 'TTS_CosyVoiceSiliconflow', 'CosyVoice Diana', 'diana', '中文', NULL, NULL, 6, NULL, NULL, NULL, NULL);

-- Update default SiliconFlow configuration to use diana voice and correct API endpoint
UPDATE `ai_model_config` 
SET config_json = '{"type": "siliconflow", "model": "FunAudioLLM/CosyVoice2-0.5B", "voice": "diana", "output_dir": "tmp/", "access_token": "", "response_format": "mp3", "speed": 1.0, "gain": 0}'
WHERE id = 'TTS_CosyVoiceSiliconflow';