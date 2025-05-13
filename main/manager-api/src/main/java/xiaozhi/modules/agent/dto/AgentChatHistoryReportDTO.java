package xiaozhi.modules.agent.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

/**
 * 小智设备聊天上报请求
 *
 * @author Haotian
 * @version 1.0, 2025/5/8
 */
@Data
@Schema(description = "小智设备聊天上报请求")
public class AgentChatHistoryReportDTO {
    @Schema(description = "MAC地址", example = "00:11:22:33:44:55")
    @NotBlank
    private String macAddress;
    @Schema(description = "会话ID", example = "79578c31-f1fb-426a-900e-1e934215f05a")
    @NotBlank
    private String sessionId;
    @Schema(description = "消息类型: 1-用户, 2-智能体", example = "1")
    @NotNull
    private Byte chatType;
    @Schema(description = "聊天内容", example = "你好呀")
    @NotBlank
    private String content;
    @Schema(description = "base64编码的opus音频数据", example = "")
    private String audioBase64;
}
