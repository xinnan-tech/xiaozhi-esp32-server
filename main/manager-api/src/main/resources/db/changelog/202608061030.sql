UPDATE `ai_model_config`
SET `config_json` = JSON_SET(`config_json`, '$.model_name', 'deepseek-v4-flash')
WHERE `id` = 'LLM_DeepSeekLLM'
  AND JSON_EXTRACT(`config_json`, '$.model_name') = 'deepseek-chat';
