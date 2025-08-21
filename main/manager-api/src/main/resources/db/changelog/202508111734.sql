-- 更新HuoshanDoubleStreamTTS供应器增加语速，音调等配置
UPDATE `ai_model_provider`
SET fields = '[{"key": "ws_url", "type": "string", "label": "WebSocket地址"}, {"key": "appid", "type": "string", "label": "应用ID"}, {"key": "access_token", "type": "string", "label": "访问令牌"}, {"key": "resource_id", "type": "string", "label": "资源ID"}, {"key": "speaker", "type": "string", "label": "默认音色"}, {"key": "speech_rate", "type": "number", "label": "语速(-50~100)"}, {"key": "loudness_rate", "type": "number", "label": "音量(-50~100)"}, {"key": "pitch", "type": "number", "label": "音高(-12~12)"}]'
WHERE id = 'SYSTEM_TTS_HSDSTTS';

UPDATE `ai_model_config` SET 
`doc_link` = 'https://console.volcengine.com/speech/service/10007',
`remark` = '火山引擎语音合成服务配置说明：
1. 访问 https://www.volcengine.com/ 注册并开通火山引擎账号
2. 访问 https://console.volcengine.com/speech/service/10007 开通语音合成大模型，购买音色
3. 在页面底部获取appid和access_token
5. 资源ID固定为：volc.service_type.10029（大模型语音合成及混音）
6. 语速：-50~100，可不填，正常默认值0，可填-50~100
7. 音量：-50~100，可不填，正常默认值0，可填-50~100
8. 音高：-12~12，可不填，正常默认值0，可填-12~12
9. 填入配置文件中' WHERE `id` = 'TTS_HuoshanDoubleStreamTTS';