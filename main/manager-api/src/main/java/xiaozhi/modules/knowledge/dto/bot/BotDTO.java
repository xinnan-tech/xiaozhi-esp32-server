package xiaozhi.modules.knowledge.dto.bot;

import lombok.*;
import io.swagger.v3.oas.annotations.media.Schema;
import java.io.Serializable;
import java.util.List;
import java.util.Map;
import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.*;

@Schema(description = "外部机器人 (Bot) 聚合 DTO")
public class BotDTO {

    // ========== 1. SearchBot (检索机器人) ==========

    // 对应 /api/v1/searchbots/ask
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "SearchBot 提问请求")
    public static class SearchAskReq implements Serializable {
        @Schema(description = "用户问题", requiredMode = Schema.RequiredMode.REQUIRED, example = "What is RAG?")
        @NotBlank(message = "问题不能为空")
        @JsonProperty("question")
        private String question;

        @Schema(description = "是否返回引用", defaultValue = "false")
        @JsonProperty("quote")
        @Builder.Default
        private Boolean quote = false;

        @Schema(description = "是否流式返回", defaultValue = "true")
        @JsonProperty("stream")
        @Builder.Default
        private Boolean stream = true;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "SearchBot 提问响应")
    public static class SearchAskVO implements Serializable {
        @Schema(description = "回答内容")
        @JsonProperty("answer")
        private String answer;

        @Schema(description = "引用来源 (Value 结构通常对应 RetrievalDTO.HitVO)")
        @JsonProperty("reference")
        private Map<String, Object> reference;
    }

    // 对应 /api/v1/searchbots/related_questions
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "相关问题请求")
    public static class RelatedQuestionReq implements Serializable {
        @Schema(description = "用户问题", requiredMode = Schema.RequiredMode.REQUIRED)
        @NotBlank(message = "问题不能为空")
        @JsonProperty("question")
        private String question;
    }

    // 对应 /api/v1/searchbots/mindmap
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "思维导图请求")
    public static class MindMapReq implements Serializable {
        @Schema(description = "用户问题", requiredMode = Schema.RequiredMode.REQUIRED)
        @NotBlank(message = "问题不能为空")
        @JsonProperty("question")
        private String question;
    }

    // ========== 2. AgentBot (嵌入式 Agent) ==========

    // 对应 /api/v1/agentbots/{id}/inputs
    @Data
    @Builder
    @AllArgsConstructor
    @Schema(description = "AgentBot 输入参数请求")
    public static class AgentInputsReq implements Serializable {
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "AgentBot 输入参数定义响应")
    public static class AgentInputsVO implements Serializable {
        @Schema(description = "表单变量定义列表")
        @JsonProperty("variables")
        private List<Map<String, Object>> variables;
    }

    // 对应 /api/v1/agentbots/{id}/completions
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "AgentBot 对话请求")
    public static class AgentCompletionReq implements Serializable {
        @Schema(description = "输入参数值")
        @JsonProperty("inputs")
        private Map<String, Object> inputs;

        @Schema(description = "用户查询", requiredMode = Schema.RequiredMode.REQUIRED)
        @NotBlank(message = "查询内容不能为空")
        @JsonProperty("question")
        private String question;

        @Schema(description = "是否流式返回", defaultValue = "true")
        @JsonProperty("stream")
        @Builder.Default
        private Boolean stream = true;

        @Schema(description = "会话 ID")
        @JsonProperty("session_id")
        private String sessionId;
    }
}
