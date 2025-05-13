package xiaozhi.modules.agent.dto;

import java.util.Date;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

/**
 * 智能体聊天记录DTO
 */
@Data
@Schema(description = "智能体聊天记录")
public class AgentChatHistoryDTO {
    @Schema(description = "创建时间")
    private Date createdAt;

    @Schema(description = "消息类型: 1-用户, 2-智能体")
    private Byte chatType;

    @Schema(description = "聊天内容")
    private String content;

    @Schema(description = "音频ID")
    private String audioId;

    @Schema(description = "MAC地址")
    private String macAddress;
}