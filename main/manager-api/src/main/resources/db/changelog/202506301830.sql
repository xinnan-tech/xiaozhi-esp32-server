-- 增加火山大模型网关VAD供应器
DELETE FROM `ai_model_provider` WHERE `id` = 'SYSTEM_VAD_VOLC_GW';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_VAD_VOLC_GW', 'VAD', 'volcengine', '火山引擎边缘大模型网关', '[{"key":"api_key","label":"网关秘钥","type":"string"},{"key":"model_name","label":"模型名称","type":"string"},{"key":"host","label":"网关域名","type":"string"},{"key":"senmatic_only","label":"仅使用语义判停","type":"boolean"},{"key":"threshold","label":"音量检测阈值","type":"number"},{"key":"min_silence_duration_ms","label":"最小静音时长","type":"number"},{"key":"max_silence_duration_ms","label":"最大静音时长","type":"number"}]', 1, 1, NOW(), 1, NOW());



-- 增加火山大模型网关VAD模型配置
DELETE FROM `ai_model_config` WHERE `id` = 'VAD_VolceAIGateway';
INSERT INTO `ai_model_config` VALUES ('VAD_VolceAIGateway', 'VAD', 'VolceAIGateway', '火山引擎边缘大模型网关', 0, 1, '{\"type\": \"volcengine\",  \"api_key\": \"火山引擎边缘大模型网关的秘钥\",  \"model_name\": \"semantic-integrity-recognition\", \"host\": \"ai-gateway.vei.volces.com\", \"senmatic_only\": false,\"threshold\": 0.5, \"min_silence_duration_ms\": 700, \"max_silence_duration_ms\": 3000}', NULL, NULL, 16, 1, NOW(), 1, NOW());

-- 火山大模型网关VAD模型配置说明文档
UPDATE `ai_model_config` SET 
`doc_link` = 'https://console.volcengine.com/vei/aigateway/',
`remark` = '火山引擎边缘大模型网关VAD配置说明：
1. 访问 https://console.volcengine.com/vei/aigateway/
2. 创建网关访问密钥（个人用户申请时注明来自小智xiaozhi-esp32-server社区，并描述使用背景，可更快获得审批，并有机会获得更多token， VAD模型需要oncall发起开白）
3. 勾选Semantic-Integrity-Recognition，网关支持一个api_key访问ASR,LLM,TTS,VLLM模型，满足智能体使用，推荐同时开通“Doubao-语音识别”、“Doubao-语音合成”、“Doubao-pro-32k-functioncall”、“Doubao-1.5-vision-pro”全量模型
4. 填入配置文件中' WHERE `id` = 'VAD_VolceAIGateway';


