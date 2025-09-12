-- 添加通义千问Qwen3-ASR-Flash语音识别服务配置
delete from `ai_model_provider` where id = 'SYSTEM_ASR_Qwen3Flash';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_ASR_Qwen3Flash', 'ASR', 'qwen3_asr_flash', 'Qwen3-ASR-Flash语音识别', '[{"key":"api_key","label":"API密钥","type":"password"},{"key":"base_url","label":"服务地址","type":"string"},{"key":"model_name","label":"模型名称","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"}]', 17, 1, NOW(), 1, NOW());

delete from `ai_model_config` where id = 'ASR_Qwen3Flash';
INSERT INTO `ai_model_config` VALUES ('ASR_Qwen3Flash', 'ASR', 'Qwen3-ASR-Flash', '通义千问语音识别服务', 0, 1, '{"type": "qwen3_asr_flash", "api_key": "", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "model_name": "qwen3-asr-flash", "output_dir": "tmp/", "enable_lid": true, "enable_itn": true}', 'https://help.aliyun.com/zh/bailian/', '支持多语言识别、歌唱识别、噪声拒识功能', 20, NULL, NULL, NULL, NULL);

-- 更新Qwen3-ASR-Flash模型配置的说明文档
UPDATE `ai_model_config` SET 
`doc_link` = 'https://bailian.console.aliyun.com/?apiKey=1&tab=doc#/doc/?type=model&url=2979031',
`remark` = '通义千问Qwen3-ASR-Flash配置说明：
1. 登录阿里云百炼平台https://bailian.console.aliyun.com/
2. 创建API-KEY  https://bailian.console.aliyun.com/#/api-key
3.Qwen3-ASR-Flash基于通义千问多模态基座，支持多语言识别、歌唱识别、噪声拒识等功能
' WHERE `id` = 'ASR_Qwen3Flash';
