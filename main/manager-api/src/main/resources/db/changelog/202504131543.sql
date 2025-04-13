-- 对0.3.0版本之前的参数进行修改
update `sys_params` set param_value = '.mp3;.wav;.p3' where  param_code = 'plugins.play_music.music_ext';
update `ai_model_config` set config_json =  '{\"type\": \"intent_llm\", \"llm\": \"LLM_ChatGLMLLM\"}' where  id = 'Intent_intent_llm';

-- 添加edge音色
delete from `ai_tts_voice` where tts_model_id = 'TTS_EdgeTTS';
INSERT INTO `ai_tts_voice` VALUES 
('TTS_EdgeTTS0001', 'TTS_EdgeTTS', 'EdgeTTS女声-晓晓', 'zh-CN-XiaoxiaoNeural', '普通话', NULL, NULL, 1, NULL, NULL, NULL, NULL),
('TTS_EdgeTTS0002', 'TTS_EdgeTTS', 'EdgeTTS男声-云扬', 'zh-CN-YunyangNeural', '普通话', NULL, NULL, 1, NULL, NULL, NULL, NULL),
('TTS_EdgeTTS0003', 'TTS_EdgeTTS', 'EdgeTTS女声-晓伊', 'zh-CN-XiaoyiNeural', '普通话', NULL, NULL, 1, NULL, NULL, NULL, NULL),
('TTS_EdgeTTS0004', 'TTS_EdgeTTS', 'EdgeTTS男声-云健', 'zh-CN-YunjianNeural', '普通话', NULL, NULL, 1, NULL, NULL, NULL, NULL),
('TTS_EdgeTTS0005', 'TTS_EdgeTTS', 'EdgeTTS男声-云希', 'zh-CN-YunxiNeural', '普通话', NULL, NULL, 1, NULL, NULL, NULL, NULL),
('TTS_EdgeTTS0006', 'TTS_EdgeTTS', 'EdgeTTS男声-云夏', 'zh-CN-YunxiaNeural', '普通话', NULL, NULL, 1, NULL, NULL, NULL, NULL),
('TTS_EdgeTTS0007', 'TTS_EdgeTTS', 'EdgeTTS女声-辽宁小贝', 'zh-CN-liaoning-XiaobeiNeural', '辽宁', NULL, NULL, 1, NULL, NULL, NULL, NULL),
('TTS_EdgeTTS0008', 'TTS_EdgeTTS', 'EdgeTTS女声-陕西小妮', 'zh-CN-shaanxi-XiaoniNeural', '陕西', NULL, NULL, 1, NULL, NULL, NULL, NULL),
('TTS_EdgeTTS0009', 'TTS_EdgeTTS', 'EdgeTTS女声-香港海佳', 'zh-HK-HiuGaaiNeural', '粤语', 'General', 'Friendly, Positive', 1, NULL, NULL, NULL, NULL),
('TTS_EdgeTTS0010', 'TTS_EdgeTTS', 'EdgeTTS女声-香港海曼', 'zh-HK-HiuMaanNeural', '粤语', 'General', 'Friendly, Positive', 1, NULL, NULL, NULL, NULL),
('TTS_EdgeTTS0011', 'TTS_EdgeTTS', 'EdgeTTS男声-香港万龙', 'zh-HK-WanLungNeural', '粤语', 'General', 'Friendly, Positive', 1, NULL, NULL, NULL, NULL);