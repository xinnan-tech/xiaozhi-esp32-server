-- liquibase formatted sql

-- changeset tykechen:202607071530
CREATE TABLE IF NOT EXISTS `ai_agent_snapshot` (
    `id` VARCHAR(32) NOT NULL COMMENT '快照ID',
    `agent_id` VARCHAR(32) NOT NULL COMMENT '智能体ID',
    `user_id` BIGINT DEFAULT NULL COMMENT '所属用户ID',
    `version_no` INT UNSIGNED NOT NULL COMMENT '版本号',
    `snapshot_data` JSON NOT NULL DEFAULT (JSON_OBJECT()) COMMENT '快照数据',
    `changed_fields` JSON DEFAULT NULL COMMENT '变更字段',
    `source` VARCHAR(32) DEFAULT 'config' COMMENT '快照来源',
    `restore_from_snapshot_id` VARCHAR(32) DEFAULT NULL COMMENT '恢复来源快照ID',
    `restore_from_version_no` INT UNSIGNED DEFAULT NULL COMMENT '恢复来源版本号',
    `creator` BIGINT DEFAULT NULL COMMENT '创建者',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_agent_version` (`agent_id`, `version_no`),
    INDEX `idx_agent_created_at` (`agent_id`, `created_at`),
    INDEX `idx_snapshot_user_created_at` (`user_id`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='智能体配置快照表';
