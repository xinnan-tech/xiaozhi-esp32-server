-- 增加一下ragflow返回的参数（创建/查询知识库时返回）
SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_rag_dataset' AND COLUMN_NAME = 'tenant_id');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE `ai_rag_dataset` ADD COLUMN `tenant_id` varchar(32) DEFAULT NULL COMMENT ''租户ID''', 'SELECT ''Column tenant_id already exists'' AS msg');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_rag_dataset' AND COLUMN_NAME = 'avatar');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE `ai_rag_dataset` ADD COLUMN `avatar` text DEFAULT NULL COMMENT ''知识库头像 (Base64)''', 'SELECT ''Column avatar already exists'' AS msg');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_rag_dataset' AND COLUMN_NAME = 'embedding_model');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE `ai_rag_dataset` ADD COLUMN `embedding_model` varchar(50) DEFAULT NULL COMMENT ''嵌入模型名称''', 'SELECT ''Column embedding_model already exists'' AS msg');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_rag_dataset' AND COLUMN_NAME = 'permission');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE `ai_rag_dataset` ADD COLUMN `permission` varchar(20) DEFAULT ''me'' COMMENT ''权限设置：me/team''', 'SELECT ''Column permission already exists'' AS msg');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_rag_dataset' AND COLUMN_NAME = 'chunk_method');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE `ai_rag_dataset` ADD COLUMN `chunk_method` varchar(50) DEFAULT NULL COMMENT ''分块方法''', 'SELECT ''Column chunk_method already exists'' AS msg');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_rag_dataset' AND COLUMN_NAME = 'parser_config');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE `ai_rag_dataset` ADD COLUMN `parser_config` text DEFAULT NULL COMMENT ''解析器配置 (JSON)''', 'SELECT ''Column parser_config already exists'' AS msg');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_rag_dataset' AND COLUMN_NAME = 'chunk_count');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE `ai_rag_dataset` ADD COLUMN `chunk_count` bigint(20) DEFAULT 0 COMMENT ''分块总数''', 'SELECT ''Column chunk_count already exists'' AS msg');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_rag_dataset' AND COLUMN_NAME = 'document_count');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE `ai_rag_dataset` ADD COLUMN `document_count` bigint(20) DEFAULT 0 COMMENT ''文档总数''', 'SELECT ''Column document_count already exists'' AS msg');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_rag_dataset' AND COLUMN_NAME = 'token_num');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE `ai_rag_dataset` ADD COLUMN `token_num` bigint(20) DEFAULT 0 COMMENT ''总 Token 数''', 'SELECT ''Column token_num already exists'' AS msg');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- 文档表 (Shadow DB for RAGFlow)
-- 留存一份文档id，把ragflow远端文档id和本地id关联起来（只是备份一份元信息链接，实际上文件内容的存储还是在ragflow）
DROP TABLE IF EXISTS `ai_rag_knowledge_document`;
CREATE TABLE `ai_rag_knowledge_document` (
     `id` varchar(36) NOT NULL COMMENT '本地唯一ID',
     `dataset_id` varchar(36) NOT NULL COMMENT '知识库ID (关联 ai_rag_dataset)',
     `document_id` varchar(64) NOT NULL COMMENT 'RAGFlow文档ID (远程ID)',
     `name` varchar(255) DEFAULT NULL COMMENT '文档名称',
     `size` bigint(20) DEFAULT NULL COMMENT '文件大小(Bytes)',
     `type` varchar(20) DEFAULT NULL COMMENT '文件类型',
     `chunk_method` varchar(50) DEFAULT NULL COMMENT '分块方法',
     `parser_config` text COMMENT '解析配置(JSON)',
     `status` varchar(10) DEFAULT '1' COMMENT '可用状态 (1:启用 0:禁用)',
     `run` varchar(32) DEFAULT 'UNSTART' COMMENT '运行状态 (UNSTART/RUNNING/CANCEL/DONE/FAIL)',
     `progress` double DEFAULT '0' COMMENT '解析进度 (0.0 ~ 1.0)',
     `thumbnail` mediumtext COMMENT '缩略图 (Base64 或 URL)',
     `process_duration` double DEFAULT '0' COMMENT '解析耗时 (单位: 秒)',
     `meta_fields` text COMMENT '自定义元数据 (JSON)',
     `source_type` varchar(32) DEFAULT 'local' COMMENT '来源类型 (local, s3, url 等)',
     `error` text COMMENT '错误信息',
     `chunk_count` int(11) DEFAULT '0' COMMENT '分块数量',
     `token_count` bigint(20) DEFAULT '0' COMMENT 'Token数量',
     `enabled` tinyint(1) DEFAULT '1' COMMENT '启用状态',
     `creator` bigint(20) DEFAULT NULL COMMENT '创建者',
     `created_at` datetime DEFAULT NULL COMMENT '创建时间',
     `updated_at` datetime DEFAULT NULL COMMENT '更新时间',
     `last_sync_at` datetime DEFAULT NULL COMMENT '最后同步时间',
     PRIMARY KEY (`id`),
     UNIQUE KEY `uk_doc_id` (`document_id`),
     KEY `idx_dataset_id` (`dataset_id`),
     KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='知识库文档表';