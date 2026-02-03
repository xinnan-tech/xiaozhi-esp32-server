-- 后续把sql相关的内容整理并入linqui
-- 这张表的作用是留存一份文档id，把ragflow远端文档id和本地id关联起来（只是备份一份元信息链接，实际上文件内容的存储还是在ragflow）
-- 文档表 (Shadow DB for RAGFlow)
CREATE TABLE `ai_rag_knowledge_document` (
  `id` varchar(36) NOT NULL COMMENT '本地唯一ID',
  `dataset_id` varchar(36) NOT NULL COMMENT '知识库ID (关联 ai_rag_dataset)',
  `document_id` varchar(64) NOT NULL COMMENT 'RAGFlow文档ID (远程ID)',
  `name` varchar(255) DEFAULT NULL COMMENT '文档名称',
  `size` bigint(20) DEFAULT NULL COMMENT '文件大小(Bytes)',
  `type` varchar(20) DEFAULT NULL COMMENT '文件类型',
  `chunk_method` varchar(50) DEFAULT NULL COMMENT '分块方法',
  `parser_config` text COMMENT '解析配置(JSON)',
  `status` tinyint(2) DEFAULT '1' COMMENT '状态 (0:未开始 1:解析中 2:取消 3:成功 4:失败)',
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