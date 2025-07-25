-- 将OpenAI供应器的thinking_type参数改为更通用的extra_body参数
-- 支持不同模型的额外参数配置
UPDATE `ai_model_provider` SET
`fields` = '[{"key":"base_url","label":"基础URL","type":"string"},{"key":"model_name","label":"模型名称","type":"string"},{"key":"api_key","label":"API密钥","type":"string"},{"key":"temperature","label":"温度","type":"number"},{"key":"max_tokens","label":"最大令牌数","type":"number"},{"key":"top_p","label":"top_p值","type":"number"},{"key":"top_k","label":"top_k值","type":"number"},{"key":"frequency_penalty","label":"频率惩罚","type":"number"},{"key":"extra_body","label":"extra_body","type":"dict"}]'
WHERE `id` = 'SYSTEM_LLM_openai';

-- 更新豆包大模型配置说明，添加extra_body参数说明
UPDATE `ai_model_config` SET 
`remark` = '豆包大模型配置说明：
1. 访问 https://console.volcengine.com/ark/region:ark+cn-beijing/openManagement
2. 开通Doubao-Seed-1.6服务
3. 访问 https://console.volcengine.com/ark/region:ark+cn-beijing/apiKey 获取API密钥
4. 填入配置文件中
5. extra_body关闭深度思考示例（默认开启）：{"thinking": {"type": "disabled"}}
注意：有免费额度500000token' 
WHERE `id` = 'LLM_DoubaoLLM';

-- 更新通义千问大模型配置说明，添加extra_body参数说明
UPDATE `ai_model_config` SET 
`remark` = '通义千问配置说明：
1. 访问 https://bailian.console.aliyun.com/?apiKey=1#/api-key
2. 获取API密钥
3. 填入配置文件中，当前配置使用qwen-turbo模型
4. 支持自定义参数：temperature=0.7, max_tokens=500, top_p=1, top_k=50
5. extra_body关闭深度思考示例：{"enable_thinking": false}'
WHERE `id` = 'LLM_AliLLM';