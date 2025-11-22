-- 知识库表
DROP TABLE IF EXISTS `ai_rag_dataset`;
CREATE TABLE `ai_rag_dataset` (
    `id` VARCHAR(32) NOT NULL COMMENT '唯一标识',
    `dataset_id` VARCHAR(64) NOT NULL COMMENT '知识库ID',
    `rag_model_id` VARCHAR(64) COMMENT 'RAG模型配置ID',
    `name` VARCHAR(100) NOT NULL COMMENT '知识库名称',
    `description` TEXT COMMENT '知识库描述',
    `status` TINYINT(1) DEFAULT 1 COMMENT '状态：0停用 1启用',
    `creator` BIGINT COMMENT '创建者',
    `created_at` DATETIME COMMENT '创建时间',
    `updater` BIGINT COMMENT '更新者',
    `updated_at` DATETIME COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_dataset_id` (`dataset_id`),
    INDEX `idx_ai_rag_dataset_status` (`status`),
    INDEX `idx_ai_rag_dataset_creator` (`creator`),
    INDEX `idx_ai_rag_dataset_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='知识库表';