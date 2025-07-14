package xiaozhi.modules.agent.vo;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

/**
 * 智能体用户个人聊天数据的VO
 */
@Data
public class AgentChatHistoryUserVO {
    @Schema(description = "聊天内容")
    private String content;

    @Schema(description = "音频ID")
    private String audioId;
}
