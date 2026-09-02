-- 修改聊天内容字段类型
ALTER TABLE ai_agent_chat_history MODIFY COLUMN content TEXT COMMENT '聊天内容';
