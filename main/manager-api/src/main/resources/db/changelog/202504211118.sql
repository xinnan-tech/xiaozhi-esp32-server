-- 删除无用模型供应器
delete from `ai_model_provider` where id = 'SYSTEM_LLM_doubao';
delete from `ai_model_provider` where id = 'SYSTEM_LLM_chatglm';
delete from `ai_model_provider` where id = 'SYSTEM_TTS_302ai';
delete from `ai_model_provider` where id = 'SYSTEM_TTS_gizwits';

-- 添加模型供应器
delete from `ai_model_provider` where id = 'SYSTEM_ASR_TencentASR';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_ASR_TencentASR', 'ASR', 'tencent', '腾讯语音识别', '[{"key":"appid","label":"应用ID","type":"string"},{"key":"secret_id","label":"Secret ID","type":"string"},{"key":"secret_key","label":"Secret Key","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"}]', 4, 1, NOW(), 1, NOW());

-- 添加腾讯语音合成模型供应器
delete from `ai_model_provider` where id = 'SYSTEM_TTS_TencentTTS';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_TTS_TencentTTS', 'TTS', 'tencent', '腾讯语音合成', '[{"key":"appid","label":"应用ID","type":"string"},{"key":"secret_id","label":"Secret ID","type":"string"},{"key":"secret_key","label":"Secret Key","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"},{"key":"region","label":"区域","type":"string"},{"key":"voice","label":"音色ID","type":"string"}]', 5, 1, NOW(), 1, NOW());

-- 添加腾讯语音合成音色
delete from `ai_tts_voice` where id = 'TTS_TencentTTS0001';
INSERT INTO `ai_tts_voice` VALUES ('TTS_TencentTTS0001', 'TTS_TencentTTS', '智瑜', '101001', '中文', NULL, NULL, 1, NULL, NULL, NULL, NULL);
