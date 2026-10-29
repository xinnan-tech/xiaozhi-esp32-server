-- 为Ollama LLM配置补充api_key键，用于鉴权网关/Ollama Cloud场景
-- 仅在未设置时添加占位值，不覆盖用户已有配置；本地Ollama无需鉴权，保持默认即可
UPDATE `ai_model_config`
SET `config_json` = JSON_SET(`config_json`, '$.api_key', 'ollama')
WHERE `id` = 'LLM_OllamaLLM' AND JSON_EXTRACT(`config_json`, '$.api_key') IS NULL;

-- 为Ollama供应商补充api_key字段定义，使管理后台新增/编辑Ollama模型时可直接填写API密钥
-- 仅在fields中尚无api_key时更新，不覆盖其他自定义字段
UPDATE `ai_model_provider`
SET `fields` = '[{"key":"model_name","label":"模型名称","type":"string"},{"key":"base_url","label":"服务地址","type":"string"},{"key":"api_key","label":"API密钥","type":"string"}]'
WHERE `id` = 'SYSTEM_LLM_ollama'
  AND JSON_SEARCH(`fields`, 'one', 'api_key', NULL, '$[*].key') IS NULL;

