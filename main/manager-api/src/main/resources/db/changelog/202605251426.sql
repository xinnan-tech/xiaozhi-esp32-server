-- 新增呼叫设备工具配置                                                                                                                            
SET @data_exists = (SELECT COUNT(*) FROM ai_model_provider WHERE id = 'SYSTEM_PLUGIN_CALL_DEVICE');                                                   
SET @sql = IF(@data_exists = 0,
    'INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`,
`update_date`) VALUES (''SYSTEM_PLUGIN_CALL_DEVICE'', ''Plugin'', ''call_device'', ''设备呼叫设备'', ''[]'', 85, 1988490863118454785, ''2026-05-18     
12:00:00'', 1988490863118454785, ''2026-05-18 12:00:00'')',
    'SELECT ''data already exists, skip'' AS msg');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- 更新系统菜单配置，增加联系人管理菜单
UPDATE sys_params
SET param_value = CAST(
    JSON_SET(
        CAST(param_value AS JSON),
        '$.addressBook',
        JSON_OBJECT(
            'name', 'feature.addressBook.name',
            'enabled', FALSE,
            'description', 'feature.addressBook.description'
        )
    ) AS CHAR
)
WHERE param_code = 'system-web.menu'
  AND NOT JSON_CONTAINS_PATH(CAST(param_value AS JSON), 'one', '$.addressBook');

-- 创建设备通讯录表
CREATE TABLE IF NOT EXISTS `ai_device_address_book` (
    `mac_address` VARCHAR(64) NOT NULL COMMENT '本设备MAC地址',
    `target_mac` VARCHAR(64) NOT NULL COMMENT '对方设备MAC地址',
    `alias` VARCHAR(64) DEFAULT NULL COMMENT '别名',
    `has_permission` TINYINT(1) DEFAULT TRUE COMMENT '是否有权限呼叫',
    `creator` BIGINT DEFAULT NULL COMMENT '创建人',
    `create_date` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updater` BIGINT DEFAULT NULL COMMENT '更新人',
    `update_date` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`mac_address`, `target_mac`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='设备通讯录表';