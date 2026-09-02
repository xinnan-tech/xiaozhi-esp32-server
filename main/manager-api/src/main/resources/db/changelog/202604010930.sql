-- 修改记忆模型名称

UPDATE `ai_model_config` SET `model_name` = '本地短期记忆（总结记忆）' WHERE `id` = 'Memory_mem_local_short';
UPDATE `ai_model_provider` SET `name` = '本地短期记忆（总结记忆）' WHERE `id` = 'SYSTEM_Memory_mem_local_short';

UPDATE `ai_model_config` SET `model_name` = '仅上报聊天记录（不总结记忆）' WHERE `id` = 'Memory_mem_report_only';
UPDATE `ai_model_provider` SET `name` = '仅上报聊天记录（不总结记忆）' WHERE `id` = 'SYSTEM_Memory_mem_report_only';
