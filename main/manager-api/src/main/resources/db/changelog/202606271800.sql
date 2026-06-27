-- 设备扩展属性表，用于持久化存储设备语言、蓝牙信标等动态状态
CREATE TABLE IF NOT EXISTS `ai_device_attribute` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT 'ID',
    `device_id` VARCHAR(64) NOT NULL COMMENT '设备ID（mac地址）',
    `attr_key` VARCHAR(64) NOT NULL COMMENT '属性key',
    `attr_value` TEXT COMMENT '属性值',
    `creator` BIGINT COMMENT '创建者',
    `create_date` DATETIME COMMENT '创建时间',
    `updater` BIGINT COMMENT '更新者',
    `update_date` DATETIME COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_device_attr` (`device_id`, `attr_key`),
    KEY `idx_device_id` (`device_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='设备扩展属性';
