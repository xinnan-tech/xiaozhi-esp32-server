-- 声音克隆表
DROP TABLE IF EXISTS `ai_voice_clone`;
CREATE TABLE `ai_voice_clone` (
    `id` VARCHAR(32) NOT NULL COMMENT '唯一标识',
    `name` VARCHAR(64) COMMENT '声音名称',
    `model_id` VARCHAR(32) COMMENT '模型id',
    `voice_id` VARCHAR(32) COMMENT '声音id',
    `user_id` BIGINT COMMENT '用户 ID（关联用户表）',
    `voice` LONGBLOB COMMENT '声音',
    `train_status` TINYINT(1) DEFAULT 0 COMMENT '训练状态：0待训练 1训练中 2训练成功 3训练失败',
    `train_error` VARCHAR(255) COMMENT '训练错误原因',
    `creator` BIGINT COMMENT '创建者 ID',
    `create_date` DATETIME COMMENT '创建时间',
    PRIMARY KEY (`id`),
    INDEX idx_ai_voice_clone_user_id_model_id_train_status (model_id,user_id, train_status),
    INDEX idx_ai_voice_clone_voice_id (voice_id),
    INDEX idx_ai_voice_clone_user_id (user_id),
    INDEX idx_ai_voice_clone_model_id_voice_id (model_id, voice_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='声音克隆表';