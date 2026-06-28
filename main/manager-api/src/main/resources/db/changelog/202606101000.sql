-- 门店表
CREATE TABLE IF NOT EXISTS `feedback_store` (
    `id` VARCHAR(64) NOT NULL COMMENT '门店ID',
    `store_code` VARCHAR(6) NOT NULL COMMENT '6位门店码(扫码用)',
    `store_name` VARCHAR(128) NOT NULL COMMENT '门店名称',
    `manager` VARCHAR(64) DEFAULT NULL COMMENT '店长',
    `shareholders` VARCHAR(256) DEFAULT NULL COMMENT '股东(逗号分隔)',
    `agent_id` VARCHAR(32) DEFAULT NULL COMMENT '绑定的智能体ID',
    `status` TINYINT(1) DEFAULT 1 COMMENT '0禁用 1启用',
    `creator` BIGINT DEFAULT NULL,
    `create_date` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updater` BIGINT DEFAULT NULL,
    `update_date` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_store_code` (`store_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='反馈门店表';

-- 员工表（关联门店）
CREATE TABLE IF NOT EXISTS `feedback_employee` (
    `id` VARCHAR(64) NOT NULL COMMENT '员工ID',
    `name` VARCHAR(64) NOT NULL COMMENT '姓名',
    `number` INT NOT NULL COMMENT '几号(员工编号)',
    `store_id` VARCHAR(64) NOT NULL COMMENT '所属门店ID',
    `employee_type` VARCHAR(32) DEFAULT 'normal' COMMENT 'manager/excellent/intern/normal',
    `status` TINYINT(1) DEFAULT 1 COMMENT '0禁用 1启用',
    `creator` BIGINT DEFAULT NULL,
    `create_date` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updater` BIGINT DEFAULT NULL,
    `update_date` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_store_id` (`store_id`),
    KEY `idx_store_number` (`store_id`, `number`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='反馈员工表';

-- 反馈记录表
CREATE TABLE IF NOT EXISTS `feedback_record` (
    `id` VARCHAR(64) NOT NULL COMMENT '记录ID',
    `session_id` VARCHAR(128) DEFAULT NULL COMMENT 'WebSocket会话ID',
    `store_id` VARCHAR(64) NOT NULL COMMENT '门店ID',
    `employee_id` VARCHAR(64) DEFAULT NULL COMMENT '员工ID',
    `device_mac` VARCHAR(32) DEFAULT NULL COMMENT '设备MAC',
    `raw_asr_text` TEXT COMMENT 'ASR原始文本',
    `cleaned_text` TEXT COMMENT '规整后文本',
    `qa_json` JSON COMMENT 'QA问答JSON',
    `review_long` TEXT COMMENT '标准版好评',
    `review_short` TEXT COMMENT '精简短评',
    `status` TINYINT(1) DEFAULT 1 COMMENT '0无效 1有效',
    `creator` BIGINT DEFAULT NULL,
    `create_date` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updater` BIGINT DEFAULT NULL,
    `update_date` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_store_id` (`store_id`),
    KEY `idx_session_id` (`session_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='客户反馈记录表';
