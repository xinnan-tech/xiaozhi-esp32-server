package xiaozhi.modules.agent.dto;

import java.time.LocalDateTime;

import lombok.Data;

/**
 * 智能体会话列表DTO
 */
@Data
public class AgentChatSessionDTO {
    /**
     * 会话ID
     */
    private String sessionId;

    /**
     * 会话时间
     */
    private LocalDateTime createdAt;

    /**
     * 聊天条数
     */
    private Integer chatCount;
}