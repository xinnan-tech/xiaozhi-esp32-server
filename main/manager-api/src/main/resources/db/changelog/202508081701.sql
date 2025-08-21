-- 添加Index-TTS-vLLM流式TTS供应器
delete from `ai_model_provider` where id = 'SYSTEM_TTS_IndexStreamTTS';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_TTS_IndexStreamTTS', 'TTS', 'index_stream', 'Index-TTS-vLLM流式语音合成', '[{"key":"api_url","label":"API服务地址","type":"string"},{"key":"voice","label":"默认音色","type":"string"},{"key":"audio_format","label":"音频格式","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"}]', 16, 1, NOW(), 1, NOW());

-- 添加Index-TTS-vLLM流式TTS模型配置
delete from `ai_model_config` where id = 'TTS_IndexStreamTTS';
INSERT INTO `ai_model_config` VALUES ('TTS_IndexStreamTTS', 'TTS', 'IndexStreamTTS', 'Index-TTS-vLLM流式语音合成', 0, 1, '{\"type\": \"index_stream\", \"api_url\": \"http://127.0.0.1:11996/tts\", \"voice\": \"jay_klee\", \"audio_format\": \"pcm\", \"output_dir\": \"tmp/\"}', NULL, NULL, 19, NULL, NULL, NULL, NULL);

-- 更新Index-TTS-vLLM流式TTS配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://github.com/Ksuriuri/index-tts-vllm',
`remark` = 'Index-TTS-vLLM流式TTS配置说明：
1. Index-TTS-vLLM是基于Index-TTS项目的vLLM推理服务，提供流式语音合成功能
2. 支持多种音色，音质自然，适合各种语音交互场景
3. 需要先部署Index-TTS-vLLM服务，然后配置API地址
4. 支持实时流式合成，具有较低的延迟
5. 支持自定义音色，可在项目assets文件夹下注册新音色
部署步骤：
1. 克隆项目：git clone https://github.com/Ksuriuri/index-tts-vllm.git
2. 安装依赖：pip install -r requirements.txt
3. 启动服务：python app.py
4. 服务默认运行在 http://127.0.0.1:11996
5. 如需其他音色，可到项目assets文件夹下注册
6. 支持多种音频格式：pcm、wav、mp3等
如需了解更多配置，请参考：https://github.com/Ksuriuri/index-tts-vllm/blob/master/README.md
' WHERE `id` = 'TTS_IndexStreamTTS';

-- 添加Index-TTS-vLLM流式TTS音色
delete from `ai_tts_voice` where tts_model_id = 'TTS_IndexStreamTTS';
-- 默认音色
INSERT INTO `ai_tts_voice` VALUES ('TTS_IndexStreamTTS_0001', 'TTS_IndexStreamTTS', 'Jay Klee', 'jay_klee', '中文及中英文混合', NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL);
