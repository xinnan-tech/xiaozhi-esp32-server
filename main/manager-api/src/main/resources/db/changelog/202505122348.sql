-- 添加总结记忆字段
ALTER TABLE `ai_agent`
ADD COLUMN `summary_memory` text COMMENT '总结记忆' AFTER `system_prompt`;

ALTER TABLE `ai_agent_template`
ADD COLUMN `summary_memory` text COMMENT '总结记忆' AFTER `system_prompt`;
