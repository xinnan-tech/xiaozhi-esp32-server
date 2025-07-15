
-- 增加PaddleSpeechTTS模型配置
delete from `ai_model_provider` where id = 'TTS_PaddleSpeechTTS';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('TTS_PaddleSpeechTTS', 'TTS', 'PaddleSpeechTTS', '百度PaddleSpeech语音合成', '[{\"type\": \"paddle_speech\", \"url\": \"请输入您的服务器地址\", \"spk_id\": \"0\", \"speed\": \"1.0\", \"volume\": \"1.0\", \"sample_rate\": \"0\", \"save_path\": \"./streaming_tts.wav\"}]', 18, 0, NOW(), 1, NOW());

delete from `ai_model_config` where id = 'TTS_PaddleSpeechTTS';
INSERT INTO `ai_model_config` VALUES ('TTS_PaddleSpeechTTS', 'TTS', 'PaddleSpeechTTS', '百度PaddleSpeech语音合成', 0, 1, '{\"type\": \"paddle_speech\", \"url\": \"请输入您的服务器地址\", \"spk_id\": \"0\", \"speed\": \"1.0\", \"volume\": \"1.0\", \"sample_rate\": \"0\", \"save_path\": \"./streaming_tts.wav\"}', NULL, NULL, 18, NULL, NULL, NULL, NULL);

-- 增加PaddleSpeechTTS模型配置
UPDATE `ai_model_config` SET
`doc_link` = 'https://github.com/PaddlePaddle/PaddleSpeech',
`remark` = 'PaddleSpeech语音合成服务配置说明：
    #框架地址 https://www.paddlepaddle.org.cn/
    #项目地址 https://github.com/PaddlePaddle/PaddleSpeech
    #SpeechServerDemo https://github.com/PaddlePaddle/PaddleSpeech/tree/develop/demos/speech_server
1. 访问 https://github.com/PaddlePaddle/PaddleSpeech 测试部署
2. SpeechServerDemo服务可参考https://github.com/PaddlePaddle/PaddleSpeech/tree/develop/demos/speech_server' WHERE `id` = 'TTS_PaddleSpeechTTS';


delete from `ai_tts_voice` where tts_model_id = 'TTS_PaddleSpeechTTS';
INSERT INTO `ai_tts_voice` VALUES ('TTS_LinkeraiTTS_0046', 'TTS_PaddleSpeechTTS', '小浆', '', '中文', NULL, NULL, 1, NULL, NULL, NULL, NULL);
