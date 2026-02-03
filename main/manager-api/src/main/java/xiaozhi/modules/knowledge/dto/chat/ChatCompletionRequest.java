package xiaozhi.modules.knowledge.dto.chat;

import java.io.Serializable;
import java.util.List;
import java.util.Map;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

/**
 * 聊天对话请求 DTO (OpenAI 兼容格式)
 */
@Data
@Schema(description = "聊天对话请求")
public class ChatCompletionRequest implements Serializable {

    @Schema(description = "模型标识 (对应 agent_id 或 bot_id)", requiredMode = Schema.RequiredMode.REQUIRED)
    @JsonProperty("model")
    private String model;

    @Schema(description = "对话消息列表", requiredMode = Schema.RequiredMode.REQUIRED)
    @JsonProperty("messages")
    private List<Message> messages;

    @Schema(description = "是否流式返回", defaultValue = "false")
    @JsonProperty("stream")
    private Boolean stream = false;

    @Schema(description = "温度系数 (0-1)", defaultValue = "0.7")
    @JsonProperty("temperature")
    private Double temperature;

    @Schema(description = "Session ID (可选，用于延续会话)")
    @JsonProperty("session_id")
    private String sessionId;

    @Schema(description = "其他RAGFlow特定参数 (可选)")
    private Map<String, Object> extra;

    @Data
    public static class Message implements Serializable {
        @Schema(description = "角色 (system, user, assistant)", requiredMode = Schema.RequiredMode.REQUIRED)
        private String role;

        @Schema(description = "内容", requiredMode = Schema.RequiredMode.REQUIRED)
        private String content;
    }
}
