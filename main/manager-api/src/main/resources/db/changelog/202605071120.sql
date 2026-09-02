-- 删除model_code为GizwitsTTS的配置
DELETE FROM `ai_model_config` WHERE `model_code` = 'GizwitsTTS';

-- 删除关联的TTS音色记录
DELETE FROM `ai_tts_voice` WHERE `tts_model_id` = 'TTS_GizwitsTTS';
DELETE FROM `ai_tts_voice` WHERE `tts_model_id` = 'TTS_ACGNTTS';
