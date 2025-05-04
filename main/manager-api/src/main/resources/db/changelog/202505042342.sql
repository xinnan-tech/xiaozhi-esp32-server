-- 添加腾讯语音合成模型供应器
delete from `ai_model_provider` where id = 'SYSTEM_TTS_TencentTTS';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_TTS_TencentTTS', 'TTS', 'tencent', '腾讯语音合成', '[{"key":"appid","label":"应用ID","type":"string"},{"key":"secret_id","label":"Secret ID","type":"string"},{"key":"secret_key","label":"Secret Key","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"},{"key":"region","label":"区域","type":"string"},{"key":"voice","label":"音色ID","type":"string"},{"key":"fast_voice_type","label":"FastVoiceType","type":"string"}]', 5, 1, NOW(), 1, NOW());
