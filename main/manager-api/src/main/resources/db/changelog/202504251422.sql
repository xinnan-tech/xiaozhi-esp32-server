-- 增加server.ota，用于配置ota地址

delete from `sys_params` where id = 100;
delete from `sys_params` where id = 101;

delete from `sys_params` where id = 106;
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (106, 'server.websocket', 'null', 'string', 1, 'websocket地址，多个用;分隔');

delete from `sys_params` where id = 107;
INSERT INTO `sys_params` (id, param_code, param_value, value_type, param_type, remark) VALUES (107, 'server.ota', 'null', 'string', 1, 'ota地址');


-- 增加固件信息表
CREATE TABLE IF NOT EXISTS `ai_ota` (
  `id` varchar(32) NOT NULL COMMENT 'ID',
  `firmware_name` varchar(100) DEFAULT NULL COMMENT '固件名称',
  `type` varchar(50) DEFAULT NULL COMMENT '固件类型',
  `version` varchar(50) DEFAULT NULL COMMENT '版本号',
  `size` bigint DEFAULT NULL COMMENT '文件大小(字节)',
  `remark` varchar(500) DEFAULT NULL COMMENT '备注/说明',
  `firmware_path` varchar(255) DEFAULT NULL COMMENT '固件路径',
  `sort` int unsigned DEFAULT '0' COMMENT '排序',
  `updater` bigint DEFAULT NULL COMMENT '更新者',
  `update_date` datetime DEFAULT NULL COMMENT '更新时间',
  `creator` bigint DEFAULT NULL COMMENT '创建者',
  `create_date` datetime DEFAULT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='固件信息表';

update ai_device set auto_update = 1;
