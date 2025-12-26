-- 为阿里百炼流式语音合成添加多语言音色配置字段
UPDATE `ai_model_provider` SET fields = '[{"key":"api_key","type":"string","label":"API密钥"},{"key":"output_dir","type":"string","label":"输出目录"},{"key":"model","type":"string","label":"模型名称"},{"key":"format","label":"音频格式","type":"string"},{"key":"sample_rate","label":"采样率","type":"number"},{"key": "volume", "type": "number", "label": "音量"},{"key": "rate", "type": "number", "label": "语速"},{"key": "pitch", "type": "number", "label": "音调"},{"key":"voice","type":"string","label":"默认音色"},{"key": "voice_zh", "type": "string", "label": "中文音色"},{"key": "voice_yue", "type": "string", "label": "粤语音色"},{"key": "voice_en", "type": "string", "label": "英语音色"},{"key": "voice_ja", "type": "string", "label": "日语音色"},{"key": "voice_ko", "type": "string", "label": "韩语音色"}]' WHERE id = 'SYSTEM_TTS_AliBLStreamTTS';

-- 更新配置说明
UPDATE `ai_model_config` SET
`doc_link` = 'https://bailian.console.aliyun.com/?apiKey=1#/api-key',
`remark` = '阿里百炼流式TTS说明：
1. 访问 https://bailian.console.aliyun.com/?apiKey=1#/api-key 创建项目并获取appkey
2. 支持实时流式合成，具有较低的延迟
3. 支持多种音色设置和音频参数调整
4. 使用FunASR进行语音识别时，可以自动选择对应语言音色
5. 支持CosyVoice-V3-Flash等大模型音色，价格实惠(1元/万字符)
6. 支持实时调节音量、语速、音调等参数
' WHERE `id` = 'TTS_AliBLStreamTTS';