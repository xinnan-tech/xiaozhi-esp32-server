-- 删除非流式MiniMax TTS配置，保留流式版本

-- 删除旧的非流式MiniMax TTS模型配置
DELETE FROM `ai_model_config` WHERE `id` = 'TTS_MinimaxTTS';

-- 删除旧的非流式MiniMax TTS供应器配置  
DELETE FROM `ai_model_provider` WHERE `id` = 'SYSTEM_TTS_minimax';

-- 删除旧的非流式MiniMax TTS音色配置
DELETE FROM `ai_tts_voice` WHERE `tts_model_id` = 'TTS_MinimaxTTS';
