-- 用户-陪伴角色匹配映射(儿童陪伴:按聊天主题自动匹配角色 + 家长手动切换)
CREATE TABLE `ai_user_persona_assignment` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `user_id` BIGINT NOT NULL COMMENT '用户ID',
    `agent_id` VARCHAR(32) NOT NULL COMMENT '当前匹配的陪伴角色(ai_agent.id)',
    `manual` TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '0=自动匹配管理;1=家长手动设定(自动任务跳过)',
    `score` DECIMAL(4,2) DEFAULT NULL COMMENT '最近匹配置信度 0~1',
    `reason` VARCHAR(255) DEFAULT NULL COMMENT '匹配理由(LLM)',
    `matched_at` DATETIME DEFAULT NULL COMMENT '最近匹配时间',
    `creator` BIGINT DEFAULT NULL,
    `create_date` DATETIME DEFAULT NULL,
    `updater` BIGINT DEFAULT NULL,
    `update_date` DATETIME DEFAULT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户-陪伴角色匹配映射';
