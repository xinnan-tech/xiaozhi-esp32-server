-- 为 LLM 的 OpenAI 接口配置表单新增 chat_template_kwargs 字段(dict, 前端映射为 JSON 文本框)
-- 用于向 vLLM/SGLang 等自托管 OpenAI 兼容后端透传 chat template 控制参数(如 enable_thinking)
-- 注意: DashScope 等云服务不识别此字段, 仅供自托管后端使用
UPDATE `ai_model_provider`
SET `fields` = '[{"key":"base_url","label":"基础URL","type":"string"},{"key":"model_name","label":"模型名称","type":"string"},{"key":"api_key","label":"API密钥","type":"string"},{"key":"temperature","label":"温度","type":"number"},{"key":"max_tokens","label":"最大令牌数","type":"number"},{"key":"top_p","label":"top_p值","type":"number"},{"key":"top_k","label":"top_k值","type":"number"},{"key":"frequency_penalty","label":"频率惩罚","type":"number"},{"key":"chat_template_kwargs","label":"模板变量(JSON)","type":"dict"}]'
WHERE `id` = 'SYSTEM_LLM_openai';
