-- Add GroqLLM Provider
DELETE FROM `ai_model_provider` WHERE id = 'SYSTEM_LLM_GroqLLM';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES
('SYSTEM_LLM_GroqLLM', 'LLM', 'groq', 'Groq LLM', '[{"key":"api_key","label":"API Key","type":"string"},{"key":"model_name","label":"Model Name","type":"string"},{"key":"base_url","label":"Base URL","type":"string"},{"key":"temperature","label":"Temperature","type":"number"},{"key":"max_tokens","label":"Max Tokens","type":"number"},{"key":"top_p","label":"Top P","type":"number"},{"key":"frequency_penalty","label":"Frequency Penalty","type":"number"},{"key":"timeout","label":"Timeout (seconds)","type":"number"},{"key":"max_retries","label":"Max Retries","type":"number"},{"key":"retry_delay","label":"Retry Delay (seconds)","type":"number"}]', 15, 1, NOW(), 1, NOW());

-- Add GroqLLM Model Configuration  
DELETE FROM `ai_model_config` WHERE id = 'LLM_GroqLLM';
INSERT INTO `ai_model_config` VALUES ('LLM_GroqLLM', 'LLM', 'GroqLLM', 'Groq LLM', 0, 1, '{"type": "openai", "api_key": "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", "model_name": "openai/gpt-oss-20b", "base_url": "https://api.groq.com/openai/v1", "temperature": 0.7, "max_tokens": 2048, "top_p": 1.0, "frequency_penalty": 0, "timeout": 15, "max_retries": 2, "retry_delay": 1}', NULL, NULL, 16, NULL, NULL, NULL, NULL);

-- Update GroqLLM Configuration Documentation
UPDATE `ai_model_config` SET 
`doc_link` = 'https://console.groq.com/',
`remark` = 'Groq LLM Configuration Guide:
1. Groq is an AI chip company focused on high-performance inference, providing fast LLM inference services
2. Supports various open-source large language models like Llama, Mixtral, etc.
3. Features ultra-low latency inference performance, suitable for real-time conversation scenarios
4. Uses OpenAI-compatible API interface for easy integration
5. Requires API key from Groq official website

Configuration Parameters:
- api_key: API key obtained from Groq console
- model_name: Model name, e.g., llama3-8b-8192, mixtral-8x7b-32768, etc.
- base_url: Groq API endpoint, typically https://api.groq.com/openai/v1
- temperature: Controls output randomness (0-2), lower values are more deterministic
- max_tokens: Maximum tokens to generate per request
- top_p: Nucleus sampling parameter controlling output diversity
- frequency_penalty: Frequency penalty to reduce repetitive content
- timeout: Request timeout in seconds, recommended 15s (Groq is fast)
- max_retries: Maximum retry attempts, recommended 2
- retry_delay: Retry interval in seconds, recommended 1s

Get API Key: https://console.groq.com/keys
Model List: https://console.groq.com/docs/models
' WHERE `id` = 'LLM_GroqLLM';