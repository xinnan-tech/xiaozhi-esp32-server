-- 使用当前主 LLM 的多模态视觉供应器。
-- 此供应器不单独配置模型或密钥，图片会作为多模态消息交给智能体配置的 LLM。
INSERT INTO `ai_model_provider`
    (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`)
SELECT 'SYSTEM_VLLM_multimodal_llm', 'VLLM', 'multimodal_llm', '使用主LLM（多模态）', '[]', 10, 1, NOW(), 1, NOW()
WHERE NOT EXISTS (
    SELECT 1 FROM `ai_model_provider` WHERE `id` = 'SYSTEM_VLLM_multimodal_llm'
);

INSERT INTO `ai_model_config`
SELECT
    'VLLM_MultimodalLLM', 'VLLM', 'MultimodalLLM', '使用主LLM（多模态）',
    0, 1, '{"type":"multimodal_llm"}', NULL, NULL, 3, NULL, NULL, NULL, NULL
WHERE NOT EXISTS (
    SELECT 1 FROM `ai_model_config` WHERE `id` = 'VLLM_MultimodalLLM'
);

UPDATE `ai_model_config`
SET `remark` = '使用当前智能体已选择的LLM处理图片和问题。请确保该LLM支持OpenAI兼容的多模态消息（text + image_url）。',
    `doc_link` = NULL
WHERE `id` = 'VLLM_MultimodalLLM';
