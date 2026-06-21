-- 注册 aipet 记忆实例（可用，不设为默认；默认记忆由各部署自行选择）
-- config_json 字段对齐 aipet.py：db_path / retrieval_mode
INSERT INTO `ai_model_config`
  (`id`, `model_type`, `model_code`, `model_name`, `is_default`, `is_enabled`, `config_json`, `sort`, `creator`, `create_date`, `updater`, `update_date`)
VALUES (
  'Memory_aipet', 'Memory', 'aipet', 'AIPet本地记忆(FTS5)', 0, 1,
  JSON_OBJECT('type', 'aipet', 'db_path', './data/xiaozhi_memory.db', 'retrieval_mode', 'fts5'),
  10, 1, NOW(), 1, NOW()
)
ON DUPLICATE KEY UPDATE
  `is_enabled` = VALUES(`is_enabled`),
  `config_json` = VALUES(`config_json`);
