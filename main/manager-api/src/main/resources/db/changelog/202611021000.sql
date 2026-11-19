-- 新增 Atlas Cloud（OpenAI 兼容网关）LLM 配置
delete from `ai_model_config` where id = 'LLM_AtlasCloudLLM';
INSERT INTO `ai_model_config` VALUES ('LLM_AtlasCloudLLM', 'LLM', 'AtlasCloudLLM', 'Atlas Cloud', 0, 1, '{"type": "openai", "base_url": "https://api.atlascloud.ai/v1", "model_name": "deepseek-ai/deepseek-v4-flash", "api_key": "你的api_key"}', 'https://www.atlascloud.ai/docs', 'Atlas Cloud 配置说明：
1. Atlas Cloud 是 OpenAI 兼容的多模型 API 网关
2. 在 https://console.atlascloud.ai/api-keys 获取 API Key
3. 可用模型列表见 https://api.atlascloud.ai/v1/models ，model_name 形如 deepseek-ai/deepseek-v4-flash
4. 填入 api_key 后保存即可使用
', 15, NULL, NULL, NULL, NULL);
