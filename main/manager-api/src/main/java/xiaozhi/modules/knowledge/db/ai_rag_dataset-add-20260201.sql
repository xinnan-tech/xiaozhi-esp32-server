--增加一下ragflow返回的参数（创建/查询知识库时返回），记录一下，为未来拓展做准备
ALTER TABLE `ai_rag_dataset`
ADD COLUMN `tenant_id` varchar(32) DEFAULT NULL COMMENT '租户ID',
ADD COLUMN `avatar` text DEFAULT NULL COMMENT '知识库头像(Base64)',
ADD COLUMN `embedding_model` varchar(50) DEFAULT NULL COMMENT '嵌入模型名称',
ADD COLUMN `permission` varchar(20) DEFAULT 'me' COMMENT '权限设置: me/team',
ADD COLUMN `chunk_method` varchar(50) DEFAULT NULL COMMENT '分块方法',
ADD COLUMN `parser_config` text DEFAULT NULL COMMENT '解析器配置(JSON)',
ADD COLUMN `chunk_count` bigint(20) DEFAULT 0 COMMENT '分块总数',
ADD COLUMN `document_count` bigint(20) DEFAULT 0 COMMENT '文档总数',
ADD COLUMN `token_num` bigint(20) DEFAULT 0 COMMENT '总Token数';