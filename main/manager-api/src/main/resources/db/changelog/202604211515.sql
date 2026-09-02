-- 智能体替换词文件表
CREATE TABLE IF NOT EXISTS `ai_agent_correct_word_file` (
    `id`          VARCHAR(32)  NOT NULL,
    `file_name`   VARCHAR(256) NOT NULL COMMENT '原始文件名',
    `word_count`  INT          NOT NULL DEFAULT 0 COMMENT '替换词数量',
    `content`     TEXT         COMMENT '文件原始内容',
    `creator`     BIGINT       DEFAULT NULL,
    `created_at`  DATETIME     DEFAULT CURRENT_TIMESTAMP,
    `updater`     BIGINT       DEFAULT NULL,
    `updated_at`  DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    INDEX `idx_creator` (`creator`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='替换词文件';

-- 替换词词条表
CREATE TABLE IF NOT EXISTS `ai_agent_correct_word_item` (
    `id`          VARCHAR(32)  NOT NULL,
    `file_id`     VARCHAR(32)  NOT NULL COMMENT '所属文件ID',
    `source_word` VARCHAR(128) NOT NULL COMMENT '原词',
    `target_word` VARCHAR(128) NOT NULL COMMENT '替换词',
    PRIMARY KEY (`id`),
    INDEX `idx_file_id` (`file_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='替换词词条';

-- 智能体替换词文件关联表
CREATE TABLE IF NOT EXISTS `ai_agent_correct_word_mapping` (
    `id`          VARCHAR(32)  NOT NULL,
    `agent_id`    VARCHAR(32)  NOT NULL,
    `file_id`     VARCHAR(32)  NOT NULL,
    `creator`     BIGINT       DEFAULT NULL,
    `created_at`  DATETIME     DEFAULT CURRENT_TIMESTAMP,
    `updater`     BIGINT       DEFAULT NULL,
    `updated_at`  DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE INDEX `uk_agent_file` (`agent_id`, `file_id`),
    INDEX `idx_agent_id` (`agent_id`),
    INDEX `idx_file_id` (`file_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='智能体替换词文件关联';
