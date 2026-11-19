-- PaddleSpeechTTS：智控台协议收敛为仅 websocket（与 xiaozhi-server 实现一致）

UPDATE `ai_model_provider`
SET `fields` = JSON_ARRAY(
    JSON_OBJECT('key', 'protocol', 'label', '协议类型', 'type', 'string', 'options', JSON_ARRAY('websocket')),
    JSON_OBJECT('key', 'url', 'label', '服务地址', 'type', 'string'),
    JSON_OBJECT('key', 'spk_id', 'label', '音色', 'type', 'int'),
    JSON_OBJECT('key', 'sample_rate', 'label', '采样率', 'type', 'float'),
    JSON_OBJECT('key', 'speed', 'label', '语速', 'type', 'float'),
    JSON_OBJECT('key', 'volume', 'label', '音量', 'type', 'float'),
    JSON_OBJECT('key', 'save_path', 'label', '保存路径', 'type', 'string')
)
WHERE `id` = 'SYSTEM_TTS_PaddleSpeechTTS';

UPDATE `ai_model_config`
SET `remark` = 'PaddleSpeechTTS 配置说明：
1. PaddleSpeech 是百度飞桨开源的语音合成工具，支持本地离线部署和模型训练。paddlepaddle百度飞浆框架地址：https://www.paddlepaddle.org.cn/
2. 当前仅支持 WebSocket 协议进行流式传输（参考部署文档：https://github.com/xinnan-tech/xiaozhi-esp32-server/blob/main/docs/paddlespeech-deploy.md）。
3. 使用前要在本地部署 paddlespeech 服务，服务默认运行在 ws://127.0.0.1:8092/paddlespeech/tts/streaming
4. 支持自定义发音人、语速、音量和采样率。
'
WHERE `id` = 'TTS_PaddleSpeechTTS';
