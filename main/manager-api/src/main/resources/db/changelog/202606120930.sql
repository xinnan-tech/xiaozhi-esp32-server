-- 1. 给 openai LLM provider 添加 cache 字段（千问显式缓存开关）
-- 在现有 fields 末尾追加 cache 字段，类型为 boolean（开关）
UPDATE `ai_model_provider` SET `fields` = JSON_ARRAY_APPEND(
    `fields`,
    '$',
    JSON_OBJECT('key', 'cache', 'label', '是否开启缓存', 'type', 'boolean')
) WHERE `id` = 'SYSTEM_LLM_openai' AND JSON_CONTAINS(
    `fields`,
    JSON_OBJECT('key', 'cache'),
    '$'
) = 0;

-- 2. 新增 doubao_cache LLM provider（豆包 Session 缓存）
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`)
VALUES (
    'SYSTEM_LLM_doubao_cache',
    'LLM',
    'doubao_cache',
    '豆包(Session缓存)',
    '[
        {"key": "base_url", "label": "基础URL", "type": "string"},
        {"key": "model_name", "label": "模型名称", "type": "string"},
        {"key": "api_key", "label": "API密钥", "type": "string"},
        {"key": "temperature", "label": "温度", "type": "number"},
        {"key": "max_tokens", "label": "最大令牌数", "type": "number"},
        {"key": "cache", "label": "是否开启缓存", "type": "boolean"}
    ]',
    50,
    1,
    NOW(),
    1,
    NOW()
);
