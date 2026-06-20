-- 注册 aipet 记忆 provider（Python 端自定义模块，运行时由 core/providers/memory/aipet/ 动态发现）
-- fields 对齐 config.yaml 的 memory.aipet 段（db_path + retrieval_mode）
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`)
VALUES (
    'SYSTEM_Memory_aipet',
    'Memory',
    'aipet',
    'AIPet本地记忆(FTS5)',
    '[{"key":"db_path","label":"数据库路径","type":"string"},{"key":"retrieval_mode","label":"检索模式","type":"string"}]',
    10,
    1,
    NOW(),
    1,
    NOW()
);
