-- 更新EdgeTTS供应器增加语速、音调、音量配置
UPDATE `ai_model_provider`
SET fields = '[{"key":"voice","label":"音色","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"},{"key":"rate","label":"语速(-100~100)","type":"number"},{"key":"volume","label":"音量(0~100)","type":"number"},{"key":"pitch","label":"音调(-100~100)","type":"number"}]'
WHERE id = 'SYSTEM_TTS_edge';

UPDATE `ai_model_config` SET
`remark` = 'EdgeTTS配置说明：
1. 使用微软Edge TTS服务
2. 支持多种语言和音色
3. 免费使用，无需注册
4. 需要网络连接
5. 输出文件保存在tmp/目录
6. 语速：-100~100，0为正常速度
7. 音量：0~100，50为正常音量
8. 音调：-100~100，0为正常音调' WHERE `id` = 'TTS_EdgeTTS';
