package xiaozhi.modules.knowledge.dto.agent;

import lombok.*;
import io.swagger.v3.oas.annotations.media.Schema;
import java.io.Serializable;
import java.util.List;
import java.util.Map;
import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.*;

@Schema(description = "智能体 (Agent) 管理聚合 DTO")
public class AgentDTO {

    // ========== 1. Agent 管理 (CRUD) - 对应 RAGFlow_Agent接口详解 ==========
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "Agent 创建请求")
    public static class CreateReq implements Serializable {
        @Schema(description = "Agent 标题", requiredMode = Schema.RequiredMode.REQUIRED, example = "My Agent")
        @NotBlank(message = "Agent 标题不能为空")
        @JsonProperty("title")
        private String title;

        @Schema(description = "DSL 定义 (画布 JSON)", requiredMode = Schema.RequiredMode.REQUIRED)
        @NotNull(message = "DSL 定义不能为空")
        @JsonProperty("dsl")
        private Map<String, Object> dsl;

        @Schema(description = "描述", example = "这是一个测试 Agent")
        @JsonProperty("description")
        private String description;

        @Schema(description = "头像 URL", example = "http://example.com/avatar.png")
        @JsonProperty("avatar")
        private String avatar;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "Agent 更新请求")
    public static class UpdateReq implements Serializable {
        @Schema(description = "Agent 标题", example = "Updated Agent")
        @JsonProperty("title")
        private String title;

        @Schema(description = "DSL 定义 (画布 JSON)")
        @JsonProperty("dsl")
        private Map<String, Object> dsl;

        @Schema(description = "描述")
        @JsonProperty("description")
        private String description;

        @Schema(description = "头像 URL")
        @JsonProperty("avatar")
        private String avatar;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "Agent 列表请求")
    public static class ListReq implements Serializable {
        @Schema(description = "页码", defaultValue = "1")
        @JsonProperty("page")
        @Builder.Default
        private Integer page = 1;

        @Schema(description = "每页大小", defaultValue = "10")
        @JsonProperty("page_size")
        @Builder.Default
        private Integer pageSize = 10;

        @Schema(description = "排序字段", defaultValue = "update_time")
        @JsonProperty("orderby")
        @Builder.Default
        private String orderby = "update_time";

        @Schema(description = "是否降序", defaultValue = "true")
        @JsonProperty("desc")
        @Builder.Default
        private Boolean desc = true;

        @Schema(description = "Agent ID 过滤")
        @JsonProperty("id")
        private String id;

        @Schema(description = "标题模糊搜索")
        @JsonProperty("title")
        private String title;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "Agent 响应对象")
    public static class AgentVO implements Serializable {
        @Schema(description = "Agent ID")
        @JsonProperty("id")
        private String id;

        @Schema(description = "标题")
        @JsonProperty("title")
        private String title;

        @Schema(description = "描述")
        @JsonProperty("description")
        private String description;

        @Schema(description = "头像")
        @JsonProperty("avatar")
        private String avatar;

        @Schema(description = "DSL 定义")
        @JsonProperty("dsl")
        private Map<String, Object> dsl;

        @Schema(description = "创建者 ID")
        @JsonProperty("user_id")
        private String userId;

        @Schema(description = "画布分类")
        @JsonProperty("canvas_category")
        private String canvasCategory;

        @Schema(description = "创建时间 (时间戳)")
        @JsonProperty("create_time")
        private Long createTime;

        @Schema(description = "更新时间 (时间戳)")
        @JsonProperty("update_time")
        private Long updateTime;
    }

    // ========== 2. Webhook 调试与追踪 - 对应 RAGFlow_Agent接口详解 ==========
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "Webhook 触发请求 (参数动态)")
    public static class WebhookTriggerReq implements Serializable {
        @Schema(description = "输入变量", requiredMode = Schema.RequiredMode.REQUIRED)
        @NotNull(message = "输入变量不能为空")
        @JsonProperty("inputs")
        private Map<String, Object> inputs;

        @Schema(description = "查询词", example = "Hello")
        @JsonProperty("query")
        private String query;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "Webhook 追踪请求")
    public static class WebhookTraceReq implements Serializable {
        @Schema(description = "时间戳游标", example = "1700000000.0")
        @JsonProperty("since_ts")
        private Double sinceTs;

        @Schema(description = "Webhook ID")
        @JsonProperty("webhook_id")
        private String webhookId;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "Webhook 追踪响应")
    public static class WebhookTraceVO implements Serializable {
        @Schema(description = "Webhook ID")
        @JsonProperty("webhook_id")
        private String webhookId;

        @Schema(description = "是否结束")
        @JsonProperty("finished")
        private Boolean finished;

        @Schema(description = "下一次查询的时间戳游标")
        @JsonProperty("next_since_ts")
        private Double nextSinceTs;

        @Schema(description = "事件列表")
        @JsonProperty("events")
        private List<TraceEvent> events;

        @Data
        @Builder
        @NoArgsConstructor
        @AllArgsConstructor
        @Schema(description = "追踪事件项")
        public static class TraceEvent implements Serializable {
            @Schema(description = "时间戳")
            @JsonProperty("ts")
            private Double ts;

            @Schema(description = "事件类型")
            @JsonProperty("event")
            private String event;

            @Schema(description = "事件数据")
            @JsonProperty("data")
            private Object data;
        }
    }

    // ========== 3. Agent 会话 (Session) - 对应 RAGFlow_Agent_Dify接口详解 ==========
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "Session 创建请求")
    public static class SessionCreateReq implements Serializable {
        @Schema(description = "用户 ID")
        @JsonProperty("user_id")
        private String userId;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "Session 列表请求")
    public static class SessionListReq implements Serializable {
        @Schema(description = "页码", defaultValue = "1")
        @JsonProperty("page")
        @Builder.Default
        private Integer page = 1;

        @Schema(description = "每页大小", defaultValue = "10")
        @JsonProperty("page_size")
        @Builder.Default
        private Integer pageSize = 10;

        @Schema(description = "排序字段", defaultValue = "create_time")
        @JsonProperty("orderby")
        @Builder.Default
        private String orderby = "create_time";

        @Schema(description = "是否降序", defaultValue = "true")
        @JsonProperty("desc")
        @Builder.Default
        private Boolean desc = true;

        @Schema(description = "Session ID")
        @JsonProperty("id")
        private String id;

        @Schema(description = "用户 ID")
        @JsonProperty("user_id")
        private String userId;

        @Schema(description = "是否返回 DSL")
        @JsonProperty("dsl")
        @Builder.Default
        private Boolean dsl = false;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "Session 批量删除请求")
    public static class SessionBatchDeleteReq implements Serializable {
        @Schema(description = "会话 ID 列表", requiredMode = Schema.RequiredMode.REQUIRED)
        @JsonProperty("ids")
        @NotEmpty(message = "ID列表不能为空")
        private List<String> ids;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "Session 响应对象")
    public static class SessionVO implements Serializable {
        @Schema(description = "Session ID")
        @JsonProperty("id")
        private String id;

        @Schema(description = "Agent ID")
        @JsonProperty("agent_id")
        private String agentId;

        @Schema(description = "用户 ID")
        @JsonProperty("user_id")
        private String userId;

        @Schema(description = "来源")
        @JsonProperty("source")
        private String source;

        @Schema(description = "DSL 定义")
        @JsonProperty("dsl")
        private Map<String, Object> dsl;

        @Schema(description = "消息列表")
        @JsonProperty("messages")
        private List<Map<String, Object>> messages;
    }

    // ========== 4. Agent 对话 (Completion) - 对应 RAGFlow_Agent_Dify接口详解 ==========
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "Completion 对话请求")
    public static class CompletionReq implements Serializable {
        @Schema(description = "会话 ID", requiredMode = Schema.RequiredMode.REQUIRED)
        @NotBlank(message = "会话 ID 不能为空")
        @JsonProperty("session_id")
        private String sessionId;

        @Schema(description = "用户问题")
        @JsonProperty("question")
        private String question;

        @Schema(description = "是否流式返回", defaultValue = "true")
        @JsonProperty("stream")
        @Builder.Default
        private Boolean stream = true;

        @Schema(description = "是否返回追踪信息", defaultValue = "false")
        @JsonProperty("return_trace")
        @Builder.Default
        private Boolean returnTrace = false;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "Completion 对话响应")
    public static class CompletionVO implements Serializable {
        @Schema(description = "会话 ID")
        @JsonProperty("id")
        private String id;

        @Schema(description = "回复内容")
        @JsonProperty("content")
        private String content;

        @Schema(description = "引用来源")
        @JsonProperty("reference")
        private Map<String, Object> reference;

        @Schema(description = "追踪信息")
        @JsonProperty("trace")
        private List<Object> trace;
    }

    // ========== 5. Dify 兼容检索 - 对应 RAGFlow_Agent_Dify接口详解 ==========
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "Dify 兼容检索请求")
    public static class DifyRetrievalReq implements Serializable {
        @Schema(description = "知识库 ID")
        @JsonProperty("knowledge_id")
        private String knowledgeId;

        @Schema(description = "查询词")
        @JsonProperty("query")
        private String query;

        @Schema(description = "检索设置")
        @JsonProperty("retrieval_setting")
        private Map<String, Object> retrievalSetting;

        @Schema(description = "元数据过滤条件")
        @JsonProperty("metadata_condition")
        private Map<String, Object> metadataCondition;

        @Schema(description = "是否使用知识图谱")
        @JsonProperty("use_kg")
        private Boolean useKg;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "Dify 兼容检索响应")
    public static class DifyRetrievalVO implements Serializable {
        @Schema(description = "检索结果列表")
        @JsonProperty("records")
        private List<Record> records;

        @Data
        @Builder
        @NoArgsConstructor
        @AllArgsConstructor
        @Schema(description = "检索记录")
        public static class Record implements Serializable {
            @Schema(description = "内容")
            @JsonProperty("content")
            private String content;

            @Schema(description = "相似度分数")
            @JsonProperty("score")
            private Double score;

            @Schema(description = "标题")
            @JsonProperty("title")
            private String title;

            @Schema(description = "元数据")
            @JsonProperty("metadata")
            private Map<String, Object> metadata;
        }
    }
}
