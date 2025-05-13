-- 初始化智能体聊天记录
DROP TABLE IF EXISTS ai_chat_history;
DROP TABLE IF EXISTS ai_chat_message;
DROP TABLE IF EXISTS ai_agent_chat_history;
CREATE TABLE ai_agent_chat_history
(
    id          BIGINT AUTO_INCREMENT COMMENT '主键ID' PRIMARY KEY,
    mac_address VARCHAR(50) COMMENT 'MAC地址',
    agent_id VARCHAR(32) COMMENT '智能体id',
    session_id  VARCHAR(50) COMMENT '会话ID',
    chat_type   TINYINT(3) COMMENT '消息类型: 1-用户, 2-智能体',
    content     VARCHAR(1024) COMMENT '聊天内容',
    audio_id    VARCHAR(32) COMMENT '音频ID',
    created_at  DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3) NOT NULL COMMENT '创建时间',
    updated_at  DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3) NOT NULL ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '更新时间',
    INDEX idx_ai_agent_chat_history_mac (mac_address),
    INDEX idx_ai_agent_chat_history_session_id (session_id),
    INDEX idx_ai_agent_chat_history_agent_id (agent_id),
    INDEX idx_ai_agent_chat_history_agent_session_created (agent_id, session_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '智能体聊天记录表';

DROP TABLE IF EXISTS ai_agent_chat_audio;
CREATE TABLE ai_agent_chat_audio
(
    id          VARCHAR(32) COMMENT '主键ID' PRIMARY KEY,
    audio       LONGBLOB COMMENT '音频opus数据'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '智能体聊天音频数据表'; 