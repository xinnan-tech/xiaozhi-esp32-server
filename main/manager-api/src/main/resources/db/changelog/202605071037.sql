-- 删除provider_code为ttson的供应器
DELETE FROM `ai_model_provider` WHERE `provider_code` = 'ttson';

-- 删除model_code为ACGNTTS的配置
DELETE FROM `ai_model_config` WHERE `model_code` = 'ACGNTTS';
