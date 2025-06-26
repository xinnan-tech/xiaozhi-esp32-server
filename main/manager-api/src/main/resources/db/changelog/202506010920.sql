-- VLLM模型供应器
delete from `ai_model_provider` where id = 'SYSTEM_VLLM_openai';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_VLLM_openai', 'VLLM', 'openai', 'OpenAI接口', '[{"key":"base_url","label":"基础URL","type":"string"},{"key":"model_name","label":"模型名称","type":"string"},{"key":"api_key","label":"API密钥","type":"string"}]', 9, 1, NOW(), 1, NOW());

-- VLLM模型配置
delete from `ai_model_config` where id = 'VLLM_ChatGLMVLLM';
INSERT INTO `ai_model_config` VALUES ('VLLM_ChatGLMVLLM', 'VLLM', 'ChatGLMVLLM', '智谱视觉AI', 1, 1, '{\"type\": \"openai\", \"model_name\": \"glm-4v-flash\", \"base_url\": \"https://open.bigmodel.cn/api/paas/v4/\", \"api_key\": \"你的api_key\"}', NULL, NULL, 1, NULL, NULL, NULL, NULL);

-- 更新文档
UPDATE `ai_model_config` SET 
`doc_link` = 'https://bigmodel.cn/usercenter/proj-mgmt/apikeys',
`remark` = '智谱视觉AI配置说明：
1. 访问 https://bigmodel.cn/usercenter/proj-mgmt/apikeys
2. 注册并获取API密钥
3. 填入配置文件中' WHERE `id` = 'VLLM_ChatGLMVLLM';


-- 添加参数
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (113, 'server.http_port', '8003', 'number', 1, 'http服务的端口，用于启动视觉分析接口');
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (114, 'server.vision_explain', 'null', 'string', 1, '视觉分析接口地址，用于下发到设备，多个用;分隔');

-- 智能体表增加VLLM模型配置
ALTER TABLE `ai_agent` 
ADD COLUMN `vllm_model_id` varchar(32) NULL DEFAULT 'VLLM_ChatGLMVLLM' COMMENT '视觉模型标识' AFTER `llm_model_id`;

-- 智能体模版表增加VLLM模型配置
ALTER TABLE `ai_agent_template` 
ADD COLUMN `vllm_model_id` varchar(32) NULL DEFAULT 'VLLM_ChatGLMVLLM' COMMENT '视觉模型标识' AFTER `llm_model_id`;