-- 增加火山大模型网关ASR供应器和模型配置
DELETE FROM `ai_model_provider` WHERE `id` = 'SYSTEM_ASR_VOLC_GW';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_ASR_VOLC_GW', 'ASR', 'volcengine', '火山引擎边缘大模型网关', '[{"key":"api_key","label":"网关秘钥","type":"string"},{"key":"model_name","label":"模型名称","type":"string"},{"key":"host","label":"网关域名","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"}]', 1, 1, NOW(), 1, NOW());

DELETE FROM `ai_model_config` WHERE `id` = 'ASR_VolceAIGateway';
INSERT INTO `ai_model_config` VALUES ('ASR_VolceAIGateway', 'ASR', 'VolceAIGateway', '火山引擎边缘大模型网关', 0, 1, '{\"type\": \"volcengine\",  \"api_key\": \"火山引擎边缘大模型网关的秘钥\",  \"model_name\": \"bigmodel\", \"host\": \"ai-gateway.vei.volces.com\", \"output_dir\": \"tmp/\"}', NULL, NULL, 16, 1, NOW(), 1, NOW());

-- 火山大模型网关ASR模型配置说明文档
UPDATE `ai_model_config` SET 
`doc_link` = 'https://console.volcengine.com/vei/aigateway/',
`remark` = '火山引擎边缘大模型网关ASR配置说明：
1. 访问 https://console.volcengine.com/vei/aigateway/
2. 创建网关访问密钥（个人用户申请时注明来自小智xiaozhi-esp32-server社区，并描述使用背景，可更快获得审批，并有机会获得更多token）
3. 搜索并勾选 Doubao-语音识别，如果需要使用LLM，一并勾选 Doubao-pro-32k-functioncall
4. 填入配置文件中' WHERE `id` = 'ASR_VolceAIGateway';

