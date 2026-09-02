-- 更新模型名称：qwen2.5-vl-3b-instruct 改为 qwen3.5-flash
UPDATE `ai_model_config` 
SET `config_json` = JSON_SET(`config_json`, '$.model_name', 'qwen3.5-flash')
WHERE `id` = 'VLLM_QwenVLVLLM' 
AND JSON_EXTRACT(`config_json`, '$.model_name') = 'qwen2.5-vl-3b-instruct';

-- 更新模型名称：qwen-turbo 改为 qwen-flash
UPDATE `ai_model_config` 
SET `config_json` = JSON_SET(`config_json`, '$.model_name', 'qwen-flash')
WHERE `id` = 'LLM_AliLLM' 
AND JSON_EXTRACT(`config_json`, '$.model_name') = 'qwen-turbo';

-- 更新备注：qwen-turbo 改为 qwen-flash
UPDATE `ai_model_config` 
SET `remark` = REPLACE(`remark`, 'qwen-turbo', 'qwen-flash')
WHERE `id` = 'LLM_AliLLM' 
AND `remark` LIKE '%qwen-turbo%';
