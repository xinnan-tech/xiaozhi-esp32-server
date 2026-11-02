-- Ollama LLM配置补充api_key占位值，走鉴权网关/Ollama Cloud时使用
UPDATE `ai_model_config`
SET `config_json` = JSON_SET(`config_json`, '$.api_key', 'ollama')
WHERE `id` = 'LLM_OllamaLLM' AND JSON_EXTRACT(`config_json`, '$.api_key') IS NULL;

-- Ollama供应商追加api_key字段定义，password类型
UPDATE `ai_model_provider`
SET `fields` = JSON_ARRAY_APPEND(COALESCE(`fields`, JSON_ARRAY()), '$',
    JSON_OBJECT('key', 'api_key', 'label', 'API密钥', 'type', 'password'))
WHERE `id` = 'SYSTEM_LLM_ollama'
  AND JSON_SEARCH(`fields`, 'one', 'api_key', NULL, '$[*].key') IS NULL;

-- 配置说明补充api_key条目
UPDATE `ai_model_config`
SET `remark` = CONCAT(`remark`, '\n4. 走鉴权网关或使用Ollama Cloud时，需填写api_key')
WHERE `id` = 'LLM_OllamaLLM'
  AND `remark` IS NOT NULL AND `remark` NOT LIKE '%api_key%';
