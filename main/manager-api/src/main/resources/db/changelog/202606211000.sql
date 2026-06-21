-- 注册 aipet 记忆实例并设为默认（FTS5 本地记忆，运行时由 core/providers/memory/aipet 自动加载 xiaozhi-memory 框架）
-- 先把其他 Memory 配置置为非默认
UPDATE `ai_model_config` SET `is_default` = 0 WHERE `model_type` = 'Memory';

-- 插入 aipet 实例（config_json 字段对齐 aipet.py：db_path / retrieval_mode）
INSERT INTO `ai_model_config`
  (`id`, `model_type`, `model_code`, `model_name`, `is_default`, `is_enabled`, `config_json`, `sort`, `creator`, `create_date`, `updater`, `update_date`)
VALUES (
  'Memory_aipet', 'Memory', 'aipet', 'AIPet本地记忆(FTS5)', 1, 1,
  JSON_OBJECT('type', 'aipet', 'db_path', './data/xiaozhi_memory.db', 'retrieval_mode', 'fts5'),
  10, 1, NOW(), 1, NOW()
)
ON DUPLICATE KEY UPDATE
  `is_default` = VALUES(`is_default`),
  `is_enabled` = VALUES(`is_enabled`),
  `config_json` = VALUES(`config_json`);
