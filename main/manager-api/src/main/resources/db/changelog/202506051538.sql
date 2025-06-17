-- 增加LinkeraiTTS供应器和模型配置
delete from `ai_model_provider` where id = 'SYSTEM_TTS_LinkeraiTTS';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_TTS_LinkeraiTTS', 'TTS', 'linkerai', 'Linkerai语音合成', '[{"key":"api_url","label":"API地址","type":"string"},{"key":"audio_format","label":"音频格式","type":"string"},{"key":"access_token","label":"访问令牌","type":"string"},{"key":"voice","label":"默认音色","type":"string"}]', 14, 1, NOW(), 1, NOW());

delete from `ai_model_config` where id = 'TTS_LinkeraiTTS';
INSERT INTO `ai_model_config` VALUES ('TTS_LinkeraiTTS', 'TTS', 'LinkeraiTTS', 'Linkerai语音合成', 0, 1, '{\"type\": \"linkerai\", \"api_url\": \"https://tts.linkerai.cn/tts\", \"audio_format\": \"pcm\", \"access_token\": \"U4YdYXVfpwWnk2t5Gp822zWPCuORyeJL\", \"voice\": \"OUeAo1mhq6IBExi\"}', NULL, NULL, 17, NULL, NULL, NULL, NULL);

-- LinkeraiTTS模型配置说明文档
UPDATE `ai_model_config` SET 
`doc_link` = 'https://tts.linkerai.cn/docs',
`remark` = 'Linkerai语音合成服务配置说明：
1. 访问 https://linkerai.cn 注册并获取访问令牌
2. 默认的access_token供测试使用，请勿用于商业用途
3. 支持声音克隆功能，可自行上传音频，填入voice参数
4. 如果voice参数为空，将使用默认声音' WHERE `id` = 'TTS_LinkeraiTTS';


delete from `ai_tts_voice` where tts_model_id = 'TTS_LinkeraiTTS';
INSERT INTO `ai_tts_voice` VALUES ('TTS_LinkeraiTTS_0001', 'TTS_LinkeraiTTS', '芷若', 'OUeAo1mhq6IBExi', '中文', NULL, NULL, 1, NULL, NULL, NULL, NULL);
