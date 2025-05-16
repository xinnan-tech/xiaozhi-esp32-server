-- 添加聊天记录配置字段
ALTER TABLE `ai_agent` 
ADD COLUMN `chat_history_conf` tinyint NOT NULL DEFAULT 0 COMMENT '聊天记录配置（0不记录 1仅记录文本 2记录文本和语音）' AFTER `system_prompt`;

ALTER TABLE `ai_agent_template` 
ADD COLUMN `chat_history_conf` tinyint NOT NULL DEFAULT 0 COMMENT '聊天记录配置（0不记录 1仅记录文本 2记录文本和语音）' AFTER `system_prompt`;