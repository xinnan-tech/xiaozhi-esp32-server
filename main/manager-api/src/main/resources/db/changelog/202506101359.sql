-- 设备指令表
DROP TABLE IF EXISTS `zy_ai_device_command`;
CREATE TABLE `zy_ai_device_command` (
    `id` VARCHAR(32) NOT NULL COMMENT '主键',
    `device_id` VARCHAR(32) NOT NULL COMMENT '设备唯一标识',
    `command_type` VARCHAR(50) COMMENT '指令类型',
    `command_content` TEXT COMMENT '指令内容',
    `is_executed` TINYINT(1) DEFAULT 0 COMMENT '是否已执行(0未执行 1已执行)',
    `creator` BIGINT COMMENT '创建者',
    `create_date` DATETIME COMMENT '创建时间',
    `updater` BIGINT COMMENT '更新者',
    `update_date` DATETIME COMMENT '更新时间',
    PRIMARY KEY (`id`),
    INDEX `idx_zy_ai_device_command_device_id` (`device_id`) COMMENT '设备ID索引，用于快速查找设备指令'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='设备指令表';