-- Add Kimi/Moonshot AI LLM and VLLM model configs

-- LLM: Kimi (Moonshot AI) - kimi-k2.5, OpenAI-compatible
DELETE FROM `ai_model_config` WHERE `id` = 'LLM_KimiLLM';
INSERT INTO `ai_model_config` VALUES ('LLM_KimiLLM', 'LLM', 'KimiLLM', 'Kimi (Moonshot AI)', 0, 1, '{"type": "openai", "model_name": "kimi-k2.5", "base_url": "https://api.moonshot.ai/v1", "api_key": "你的api_key"}', NULL, NULL, 14, NULL, NULL, NULL, NULL);

-- LLM: Kimi Code Plan - optimized for coding tasks
DELETE FROM `ai_model_config` WHERE `id` = 'LLM_KimiCodePlanLLM';
INSERT INTO `ai_model_config` VALUES ('LLM_KimiCodePlanLLM', 'LLM', 'KimiCodePlanLLM', 'Kimi Code Plan', 0, 1, '{"type": "openai", "model_name": "kimi-for-coding", "base_url": "https://api.kimi.com/coding/v1", "api_key": "你的api_key"}', NULL, NULL, 15, NULL, NULL, NULL, NULL);

-- VLLM: Kimi (Moonshot AI) - kimi-k2.5 multimodal
DELETE FROM `ai_model_config` WHERE `id` = 'VLLM_KimiVLLM';
INSERT INTO `ai_model_config` VALUES ('VLLM_KimiVLLM', 'VLLM', 'KimiVLLM', 'Kimi视觉模型', 0, 1, '{"type": "openai", "model_name": "kimi-k2.5", "base_url": "https://api.moonshot.ai/v1", "api_key": "你的api_key"}', NULL, NULL, 3, NULL, NULL, NULL, NULL);
