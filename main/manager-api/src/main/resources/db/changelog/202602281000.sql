-- 标签表
CREATE TABLE IF NOT EXISTS ai_agent_tag (
    id VARCHAR(32) NOT NULL COMMENT '主键',
    tag_name VARCHAR(64) NOT NULL COMMENT '标签名称',
    sort INT UNSIGNED DEFAULT 0 COMMENT '排序',
    creator BIGINT COMMENT '创建者',
    created_at DATETIME COMMENT '创建时间',
    updater BIGINT COMMENT '更新者',
    updated_at DATETIME COMMENT '更新时间',
    deleted TINYINT DEFAULT 0 COMMENT '删除标记',
    PRIMARY KEY (id),
    UNIQUE KEY uk_tag_name (tag_name),
    INDEX idx_sort (sort)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='智能体标签表';

-- 智能体标签关联表
CREATE TABLE IF NOT EXISTS ai_agent_tag_relation (
    id VARCHAR(32) NOT NULL COMMENT '主键',
    agent_id VARCHAR(32) NOT NULL COMMENT '智能体ID',
    tag_id VARCHAR(32) NOT NULL COMMENT '标签ID',
    creator BIGINT COMMENT '创建者',
    created_at DATETIME COMMENT '创建时间',
    updater BIGINT COMMENT '更新者',
    updated_at DATETIME COMMENT '更新时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_agent_tag (agent_id, tag_id),
    INDEX idx_agent_id (agent_id),
    INDEX idx_tag_id (tag_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='智能体标签关联表';
