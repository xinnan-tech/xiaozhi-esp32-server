-- agent 扩展字段(键值对 JSON,作为 system_prompt 模板变量 {{ext.key}} 的来源)
CREATE TABLE `ai_agent_ext` (
    `agent_id` VARCHAR(32) NOT NULL COMMENT '关联 agent(一对一)',
    `ext_json` TEXT COMMENT '扩展字段 JSON 对象 {key:value}',
    `creator` BIGINT DEFAULT NULL,
    `create_date` DATETIME DEFAULT NULL,
    `updater` BIGINT DEFAULT NULL,
    `update_date` DATETIME DEFAULT NULL,
    PRIMARY KEY (`agent_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='agent 扩展字段';
