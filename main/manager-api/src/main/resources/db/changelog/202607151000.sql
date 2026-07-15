-- 设备扩展字段(孩子信息+家长期望,作为冷启动匹配信号 + prompt 注入变量 {{ext.key}} 的来源)
CREATE TABLE `ai_device_ext` (
    `device_id` VARCHAR(32) NOT NULL COMMENT '关联设备(一对一)',
    `ext_json` TEXT COMMENT '设备扩展字段 JSON {childAgeRange,childPersonality,parentGoals,parentConcerns,contentPreference}',
    `creator` BIGINT DEFAULT NULL,
    `create_date` DATETIME DEFAULT NULL,
    `updater` BIGINT DEFAULT NULL,
    `update_date` DATETIME DEFAULT NULL,
    PRIMARY KEY (`device_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='设备扩展字段(孩子信息+家长期望)';

-- ai_user_persona_assignment 扩列:支持 template 匹配 + 漂移 + 兜底标记 + 匹配来源
ALTER TABLE `ai_user_persona_assignment` ADD COLUMN `matched_template_id` VARCHAR(32) DEFAULT NULL COMMENT '匹配的乐宝模板id';
ALTER TABLE `ai_user_persona_assignment` ADD COLUMN `divergence_score` DECIMAL(4,2) DEFAULT NULL COMMENT '画像与当前模板的偏差分(0~1)';
ALTER TABLE `ai_user_persona_assignment` ADD COLUMN `fallback_flag` TINYINT DEFAULT 0 COMMENT '1=角色不足已兜底(通知管理员)';
ALTER TABLE `ai_user_persona_assignment` ADD COLUMN `match_source` VARCHAR(32) DEFAULT NULL COMMENT '匹配来源 cold_start/cold_start_default/weekly/manual';

-- ai_agent_template 加结构化匹配元数据列
ALTER TABLE `ai_agent_template` ADD COLUMN `match_meta_json` TEXT COMMENT '结构化匹配元数据 {ageRange,personalityTags,guidanceGoals,emotionalSupportLevel,languageComplexity}';

-- 录入5个乐宝模板的 match_meta_json(从 prompt 头结构化)
UPDATE `ai_agent_template` SET `match_meta_json` = '{"ageRange":"3-6","personalityTags":["情绪敏感","需要安抚"],"guidanceGoals":["情绪认知","情绪表达","情绪管理"],"emotionalSupportLevel":"高","languageComplexity":"简单柔和"}' WHERE `id` = 'adcd496218cad1b0fccceaf448219f70';
UPDATE `ai_agent_template` SET `match_meta_json` = '{"ageRange":"4-7","personalityTags":["活泼好动","喜欢挑战"],"guidanceGoals":["勇气","团队感","任务完成"],"emotionalSupportLevel":"中","languageComplexity":"适中活力"}' WHERE `id` = 'd8cdcfee5328757eaf292e923ea39d2a';
UPDATE `ai_agent_template` SET `match_meta_json` = '{"ageRange":"4-7","personalityTags":["喜欢表达","愿意社交"],"guidanceGoals":["语言表达","社交技能","文化认知"],"emotionalSupportLevel":"中高","languageComplexity":"适中丰富"}' WHERE `id` = '454f5c98cfc28db722b47e9d636b2638';
UPDATE `ai_agent_template` SET `match_meta_json` = '{"ageRange":"3-6","personalityTags":["外向活泼","精力旺盛"],"guidanceGoals":["专注力","想象力","规则意识"],"emotionalSupportLevel":"中","languageComplexity":"简单有趣"}' WHERE `id` = '317af2fa158fce067f03c389bf3c36a8';
UPDATE `ai_agent_template` SET `match_meta_json` = '{"ageRange":"4-7","personalityTags":["好奇心强","爱问为什么"],"guidanceGoals":["科学思维","观察力","逻辑推理"],"emotionalSupportLevel":"中","languageComplexity":"适中偏慢"}' WHERE `id` = 'c91712da020fc660afa5f8a9e1e928d6';
