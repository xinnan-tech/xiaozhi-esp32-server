package xiaozhi.modules.knowledge.dto.chat;

import lombok.*;
import io.swagger.v3.oas.annotations.media.Schema;
import java.io.Serializable;
import java.util.List;
import java.util.Map;
import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.*;

/**
 * 对话管理聚合 DTO
 * <p>
 * 容器类，内含对话助手、会话和消息的所有请求/响应对象。
 * </p>
 */
@Schema(description = "对话管理聚合 DTO")
public class ChatDTO {

    // ========== 1. 对话助手 (Assistant/Bot) 相关 ==========

    /**
     * 提示词配置
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    @Schema(description = "提示词配置")
    public static class PromptConfig implements Serializable {

        @Schema(description = "系统提示词", example = "你是一个专业的客服助手...")
        @JsonProperty("prompt")
        private String systemPrompt;

        @Schema(description = "开场白", example = "您好，我是您的智能助手，请问有什么可以帮您？")
        private String opener;

        @Schema(description = "空结果回复", example = "抱歉，我没有找到相关信息。")
        @JsonProperty("empty_response")
        private String emptyResponse;

        @Schema(description = "是否展示引用", example = "true")
        @JsonProperty("show_quote")
        private Boolean quote;

        @Schema(description = "是否启用 TTS", example = "false")
        private Boolean tts;

        @Schema(description = "相似度阈值 (0.0 - 1.0)", example = "0.2")
        @JsonProperty("similarity_threshold")
        private Float similarityThreshold;

        @Schema(description = "关键词相似度权重 (0.0 - 1.0)", example = "0.7")
        @JsonProperty("keywords_similarity_weight")
        private Float vectorSimilarityWeight;

        @Schema(description = "检索 Top N", example = "6")
        @JsonProperty("top_n")
        private Integer topK;

        @Schema(description = "Rerank 模型", example = "rerank_model_001")
        @JsonProperty("rerank_model")
        private String rerankId;

        @Schema(description = "是否启用多轮对话优化", example = "false")
        @JsonProperty("refine_multiturn")
        private Boolean refineMultigraph;

        @Schema(description = "变量列表")
        private List<Map<String, Object>> variables;
    }

    /**
     * LLM 配置
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    @Schema(description = "LLM 模型配置")
    public static class LLMConfig implements Serializable {

        @NotBlank(message = "模型名称不能为空")
        @Schema(description = "模型名称", requiredMode = Schema.RequiredMode.REQUIRED, example = "gpt-4")
        @JsonProperty("model_name")
        private String modelName;

        @Schema(description = "温度参数 (0.0 - 2.0)", example = "0.7")
        private Float temperature;

        @Schema(description = "Top P 采样", example = "0.9")
        @JsonProperty("top_p")
        private Float topP;

        @Schema(description = "最大 Token 数", example = "4096")
        @JsonProperty("max_tokens")
        private Integer maxTokens;

        @Schema(description = "存在惩罚", example = "0.0")
        @JsonProperty("presence_penalty")
        private Float presencePenalty;

        @Schema(description = "频率惩罚", example = "0.0")
        @JsonProperty("frequency_penalty")
        private Float frequencyPenalty;
    }

    /**
     * 创建助手请求
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    @Schema(description = "创建助手请求")
    public static class AssistantCreateReq implements Serializable {

        @NotBlank(message = "助手名称不能为空")
        @Schema(description = "助手名称", requiredMode = Schema.RequiredMode.REQUIRED, example = "智能客服助手")
        private String name;

        @Schema(description = "助手头像 (Base64 编码)", example = "")
        private String avatar;

        @Schema(description = "关联的知识库 ID 列表", example = "[\"kb_001\", \"kb_002\"]")
        @JsonProperty("dataset_ids")
        private List<String> datasetIds;

        @Schema(description = "助手描述", example = "这是一个智能客服助手")
        private String description;

        @Schema(description = "LLM 模型配置")
        @JsonProperty("llm")
        private LLMConfig llm;

        @Schema(description = "提示词配置")
        @JsonProperty("prompt")
        private PromptConfig promptConfig;
    }

    /**
     * 更新助手请求
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    @Schema(description = "更新助手请求")
    public static class AssistantUpdateReq implements Serializable {

        @Schema(description = "助手名称", example = "智能客服助手 V2")
        private String name;

        @Schema(description = "助手头像 (Base64 编码)", example = "")
        private String avatar;

        @Schema(description = "关联的知识库 ID 列表", example = "[\"kb_001\", \"kb_002\"]")
        @JsonProperty("dataset_ids")
        private List<String> datasetIds;

        @Schema(description = "助手描述", example = "这是一个智能客服助手")
        private String description;

        @Schema(description = "LLM 模型配置")
        @JsonProperty("llm")
        private LLMConfig llm;

        @Schema(description = "提示词配置")
        @JsonProperty("prompt")
        private PromptConfig promptConfig;
    }

    /**
     * 查询助手列表请求
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    @Schema(description = "查询助手列表请求")
    public static class AssistantListReq implements Serializable {

        @Schema(description = "页码 (从 1 开始)", example = "1")
        private Integer page;

        @Schema(description = "每页数量", example = "30")
        @JsonProperty("page_size")
        private Integer pageSize;

        @Schema(description = "按名称过滤 (模糊匹配)", example = "客服")
        private String name;

        @Schema(description = "排序字段: create_time / update_time", example = "create_time")
        private String orderby;

        @Schema(description = "是否降序", example = "true")
        private Boolean desc;

        @Schema(description = "按 ID 精确筛选", example = "assistant_001")
        private String id;
    }

    /**
     * 助手详情 VO
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    @Schema(description = "助手详情 VO")
    public static class AssistantVO implements Serializable {

        @Schema(description = "助手 ID", example = "assistant_001")
        private String id;

        @Schema(description = "租户 ID", example = "tenant_001")
        @JsonProperty("tenant_id")
        private String tenantId;

        @Schema(description = "助手名称", example = "智能客服助手")
        private String name;

        @Schema(description = "助手头像", example = "")
        private String avatar;

        @Schema(description = "关联的知识库 ID 列表")
        @JsonProperty("dataset_ids")
        private List<String> datasetIds;

        @Schema(description = "关联的知识库列表 (详情)")
        private List<SimpleDatasetVO> datasets;

        @Schema(description = "助手描述")
        private String description;

        @Schema(description = "LLM 模型配置")
        @JsonProperty("llm")
        private LLMConfig llm;

        @Schema(description = "提示词配置")
        @JsonProperty("prompt")
        private PromptConfig promptConfig;

        @Schema(description = "创建时间 (时间戳)", example = "1700000000000")
        @JsonProperty("create_time")
        private Long createTime;

        @Schema(description = "更新时间 (时间戳)", example = "1700000001000")
        @JsonProperty("update_time")
        private Long updateTime;
    }

    /**
     * 删除助手请求
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    @Schema(description = "删除助手请求")
    public static class AssistantDeleteReq implements Serializable {

        @Schema(description = "要删除的助手 ID 列表", example = "[\"assistant_001\", \"assistant_002\"]")
        private List<String> ids;
    }

    // ========== 2. 会话 (Session) 相关 ==========

    /**
     * 创建会话请求
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    @Schema(description = "创建会话请求")
    public static class SessionCreateReq implements Serializable {

        @Schema(description = "会话名称", example = "技术咨询会话")
        private String name;

        @Schema(description = "用户 ID", example = "user_001")
        @JsonProperty("user_id")
        private String userId;
    }

    /**
     * 更新会话请求
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    @Schema(description = "更新会话请求")
    public static class SessionUpdateReq implements Serializable {

        @Schema(description = "会话名称", example = "技术咨询会话 - 更新")
        private String name;
    }

    /**
     * 查询会话列表请求
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    @Schema(description = "查询会话列表请求")
    public static class SessionListReq implements Serializable {

        @Schema(description = "助手 ID", example = "assistant_001")
        @JsonProperty("assistant_id")
        private String assistantId;

        @Schema(description = "页码 (从 1 开始)", example = "1")
        private Integer page;

        @Schema(description = "每页数量", example = "30")
        @JsonProperty("page_size")
        private Integer pageSize;

        @Schema(description = "按名称过滤", example = "技术")
        private String name;

        @Schema(description = "排序字段", example = "create_time")
        private String orderby;

        @Schema(description = "是否降序", example = "true")
        private Boolean desc;

        @Schema(description = "会话 ID 精确筛选", example = "session_001")
        private String id;

        @Schema(description = "用户标识筛选", example = "user_001")
        @JsonProperty("user_id")
        private String userId;
    }

    /**
     * 会话详情 VO
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    @Schema(description = "会话详情 VO")
    public static class SessionVO implements Serializable {

        @Schema(description = "会话 ID", example = "session_001")
        private String id;

        @Schema(description = "助手 ID", example = "assistant_001")
        @JsonProperty("chat_id")
        private String chatId;

        @Schema(description = "助手 ID (兼容旧版)", example = "assistant_001")
        @JsonProperty("assistant_id")
        private String assistantId;

        @Schema(description = "会话名称", example = "技术咨询会话")
        private String name;

        @Schema(description = "创建时间 (时间戳)", example = "1700000000000")
        @JsonProperty("create_time")
        private Long createTime;

        @Schema(description = "更新时间 (时间戳)", example = "1700000001000")
        @JsonProperty("update_time")
        private Long updateTime;

        @Schema(description = "创建日期", example = "2024-05-01 10:00:00")
        @JsonProperty("create_date")
        private String createDate;

        @Schema(description = "更新日期", example = "2024-05-01 10:00:00")
        @JsonProperty("update_date")
        private String updateDate;

        @Schema(description = "用户 ID", example = "user_001")
        @JsonProperty("user_id")
        private String userId;

        @Schema(description = "对话历史消息列表")
        private List<Map<String, Object>> messages;
    }

    /**
     * 删除会话请求
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    @Schema(description = "删除会话请求")
    public static class SessionDeleteReq implements Serializable {

        @Schema(description = "要删除的会话 ID 列表", example = "[\"session_001\", \"session_002\"]")
        private List<String> ids;
    }

    // ========== 3. 消息/对话 (Completion) 相关 ==========

    /**
     * 发送消息请求
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    @Schema(description = "发送消息请求")
    public static class CompletionReq implements Serializable {

        @NotBlank(message = "问题内容不能为空")
        @Schema(description = "用户问题", requiredMode = Schema.RequiredMode.REQUIRED, example = "请介绍一下你们的产品")
        private String question;

        @Schema(description = "是否使用流式响应 (SSE)", example = "true")
        @Builder.Default
        private Boolean stream = true;

        @NotBlank(message = "会话 ID 不能为空")
        @Schema(description = "会话 ID (可选，不传则创建新会话)", example = "session_001")
        @JsonProperty("session_id")
        private String sessionId;

        @Schema(description = "是否展示引用", example = "true")
        private Boolean quote;

        @Schema(description = "指定检索的文档 ID 列表 (逗号分隔)", example = "doc_001,doc_002")
        @JsonProperty("doc_ids")
        private String docIds;

        @Schema(description = "元数据过滤条件")
        @JsonProperty("metadata_condition")
        private Map<String, Object> metadataCondition;
    }

    /**
     * 消息响应 VO
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    @Schema(description = "消息响应 VO")
    public static class CompletionVO implements Serializable {

        @Schema(description = "AI 回答内容")
        private String answer;

        @Schema(description = "引用信息")
        private Reference reference;

        @Schema(description = "会话 ID", example = "session_001")
        @JsonProperty("session_id")
        private String sessionId;

        @Schema(description = "任务 ID (用于流式响应追踪)", example = "task_001")
        @JsonProperty("task_id")
        private String taskId;

        /**
         * 引用信息 (检索命中结果)
         */
        @Data
        @NoArgsConstructor
        @AllArgsConstructor
        @Builder
        @Schema(description = "引用信息")
        public static class Reference implements Serializable {

            @Schema(description = "命中的文档块列表")
            private List<xiaozhi.modules.knowledge.dto.document.RetrievalDTO.HitVO> chunks;

            @Schema(description = "文档聚合信息")
            @JsonProperty("doc_aggs")
            private List<DocAgg> docAggs;
        }

        /**
         * 文档聚合信息
         */
        @Data
        @NoArgsConstructor
        @AllArgsConstructor
        @Builder
        @Schema(description = "文档聚合信息")
        public static class DocAgg implements Serializable {

            @Schema(description = "文档 ID", example = "doc_001")
            @JsonProperty("doc_id")
            private String docId;

            @Schema(description = "文档名称", example = "产品手册.pdf")
            @JsonProperty("doc_name")
            private String docName;

            @Schema(description = "命中次数", example = "3")
            private Integer count;
        }
    }

    /**
     * 简易知识库 VO (用于 Assistant 列表)
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    @Schema(description = "简易知识库 VO")
    public static class SimpleDatasetVO implements Serializable {
        @Schema(description = "知识库 ID")
        private String id;
        @Schema(description = "知识库名称")
        private String name;
        @Schema(description = "头像")
        private String avatar;
        @Schema(description = "分块数量")
        @JsonProperty("chunk_num")
        private Integer chunkNum;
    }
}
