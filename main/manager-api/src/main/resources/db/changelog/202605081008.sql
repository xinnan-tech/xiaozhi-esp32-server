-- 删除provider_code为linkerai的供应商配置
DELETE FROM `ai_model_provider` WHERE `provider_code` = 'linkerai';

-- 删除model_code为LinkeraiTTS的模型配置
DELETE FROM `ai_model_config` WHERE `model_code` = 'LinkeraiTTS';

-- 删除LinkeraiTTS关联的TTS音色记录
DELETE FROM `ai_tts_voice` WHERE `tts_model_id` = 'TTS_LinkeraiTTS';
