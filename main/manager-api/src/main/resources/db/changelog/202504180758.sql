-- 本文件用于初始化固件信息表，无需手动执行，在项目启动时会自动执行
-- -------------------------------------------------------
-- 初始化固件信息表
drop table if exists `ai_ota`;
CREATE TABLE `ai_ota` (
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='固件信息表';
