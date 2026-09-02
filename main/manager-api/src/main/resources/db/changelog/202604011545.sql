-- 智能体表添加小模型ID字段
SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_agent' AND COLUMN_NAME = 'slm_model_id');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE `ai_agent` ADD COLUMN `slm_model_id` VARCHAR(255) NULL COMMENT ''小模型ID'' AFTER `llm_model_id`', 'SELECT ''Column slm_model_id already exists'' AS msg');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- 创建聊天标题表
DROP TABLE IF EXISTS `ai_agent_chat_title`;
CREATE TABLE `ai_agent_chat_title` (
    `id` VARCHAR(32) NOT NULL COMMENT '主键ID',
    `session_id` VARCHAR(255) NOT NULL COMMENT '会话ID',
    `title` VARCHAR(255) DEFAULT NULL COMMENT '聊天标题',
    `created_at` DATETIME DEFAULT NULL COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT NULL COMMENT '更新时间',
    PRIMARY KEY (`id`),
    KEY `idx_session_id` (`session_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='智能体聊天标题表';
