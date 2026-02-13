package xiaozhi.modules.knowledge.dto.dataset;

import lombok.*;
import io.swagger.v3.oas.annotations.media.Schema;
import java.io.Serializable;
import java.util.List;
import java.util.Map;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import jakarta.validation.constraints.*;

/**
 * 知识库管理聚合 DTO
 * <p>
 * 容器类，内含知识库模块所有请求/响应对象的静态内部类定义。
 * </p>
 */
@Schema(description = "知识库管理聚合 DTO")
@JsonIgnoreProperties(ignoreUnknown = true)
public class DatasetDTO {

    // ========== 通用内部类 ==========

    /**
     * 解析器配置
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    @Schema(description = "解析器配置")
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class ParserConfig implements Serializable {

        @Schema(description = "分块 token 数量", example = "128")
        @JsonProperty("chunk_token_num")
        private Integer chunkTokenNum;

        @Schema(description = "分隔符", example = "\\n!?;。；！？")
        private String delimiter;

        @Schema(description = "布局识别模型: DeepDOC / Simple", example = "DeepDOC")
        @JsonProperty("layout_recognize")
        private String layoutRecognize;

        @Schema(description = "是否将 Excel 转为 HTML", example = "false")
        private Boolean html4excel;

        @Schema(description = "自动生成关键词数量 (0 表示关闭)", example = "0")
        @JsonProperty("auto_keywords")
        private Integer autoKeywords;

        @Schema(description = "自动生成问题数量 (0 表示关闭)", example = "0")
        @JsonProperty("auto_questions")
        private Integer autoQuestions;
    }

    // ========== 请求类 ==========

    /**
     * 创建知识库请求 (映射接口 1: create)
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    @Schema(description = "创建知识库请求")
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class CreateReq implements Serializable {

        @NotBlank(message = "知识库名称不能为空")
        @Schema(description = "知识库名称", requiredMode = Schema.RequiredMode.REQUIRED, example = "my_dataset")
        private String name;

        @Schema(description = "知识库头像 (Base64 编码)", example = "")
        private String avatar;

        @Schema(description = "知识库描述", example = "用于存储产品文档")
        private String description;

        @Schema(description = "嵌入模型名称", example = "BAAI/bge-large-zh-v1.5")
        @JsonProperty("embedding_model")
        private String embeddingModel;

        @Schema(description = "权限设置: me / team", example = "me")
        private String permission;

        @Schema(description = "分块方法: naive / manual / qa / table / paper / book / laws / presentation / picture / one / knowledge_graph / email", example = "naive")
        @JsonProperty("chunk_method")
        private String chunkMethod;

        @Schema(description = "解析器配置")
        @JsonProperty("parser_config")
        private ParserConfig parserConfig;
    }

    /**
     * 更新知识库请求 (映射接口 4: update)
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    @Schema(description = "更新知识库请求")
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class UpdateReq implements Serializable {

        @Schema(description = "知识库名称", example = "updated_dataset")
        private String name;

        @Schema(description = "知识库头像 (Base64 编码)", example = "")
        private String avatar;

        @Schema(description = "知识库描述", example = "更新后的描述")
        private String description;

        @Schema(description = "权限设置: me / team", example = "team")
        private String permission;

        @Schema(description = "嵌入模型名称", example = "BAAI/bge-large-zh-v1.5")
        @JsonProperty("embedding_model")
        private String embeddingModel;

        @Schema(description = "分块方法: naive / manual / qa / table / paper / book / laws / presentation / picture / one / knowledge_graph / email", example = "naive")
        @JsonProperty("chunk_method")
        private String chunkMethod;

        @Schema(description = "解析器配置")
        @JsonProperty("parser_config")
        private ParserConfig parserConfig;

        @Schema(description = "PageRank 权重 (0-100)", example = "50")
        private Integer pagerank;
    }

    /**
     * 查询知识库列表请求 (映射接口 3: list_datasets)
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    @Schema(description = "查询知识库列表请求")
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class ListReq implements Serializable {

        @Schema(description = "页码 (从 1 开始)", example = "1")
        private Integer page;

        @Schema(description = "每页数量", example = "30")
        @JsonProperty("page_size")
        private Integer pageSize;

        @Schema(description = "排序字段: create_time / update_time", example = "create_time")
        private String orderby;

        @Schema(description = "是否降序", example = "true")
        private Boolean desc;

        @Schema(description = "按名称过滤 (模糊匹配)", example = "my_dataset")
        private String name;

        @Schema(description = "按知识库 ID 过滤", example = "abc123")
        private String id;
    }

    /**
     * 批量删除知识库请求 (映射接口 2: delete)
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    @Schema(description = "批量删除知识库请求")
    public static class BatchIdReq implements Serializable {

        @NotNull(message = "知识库 ID 列表不能为空")
        @Size(min = 1, message = "至少需要一个知识库 ID")
        @Schema(description = "知识库 ID 列表", requiredMode = Schema.RequiredMode.REQUIRED, example = "[\"id1\", \"id2\"]")
        private List<String> ids;
    }

    /**
     * 运行 GraphRAG 请求
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    @Schema(description = "运行 GraphRAG 请求")
    public static class RunGraphRagReq implements Serializable {

        @Schema(description = "实体类型列表", example = "[\"person\", \"organization\"]")
        @JsonProperty("entity_types")
        private List<String> entityTypes;

        @Schema(description = "构建方法: light / fast / full", example = "light")
        private String method;
    }

    /**
     * 运行 RAPTOR 请求
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    @Schema(description = "运行 RAPTOR 请求")
    public static class RunRaptorReq implements Serializable {

        @Schema(description = "最大聚类数", example = "64")
        @JsonProperty("max_cluster")
        private Integer maxCluster;

        @Schema(description = "自定义提示词", example = "请总结以下内容...")
        private String prompt;
    }

    /**
     * 异步任务 ID 响应 VO (映射接口 7/8: run_graphrag/run_raptor)
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    @Schema(description = "异步任务 ID 响应")
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class TaskIdVO implements Serializable {

        @Schema(description = "GraphRAG 任务 ID", example = "task_uuid_12345678")
        @JsonProperty("graphrag_task_id")
        private String graphragTaskId;

        @Schema(description = "RAPTOR 任务 ID", example = "task_uuid_87654321")
        @JsonProperty("raptor_task_id")
        private String raptorTaskId;
    }

    // ========== 响应类 ==========

    /**
     * 知识库详情 VO (映射接口 1/3 的返回数据项)
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    @Schema(description = "知识库详情 VO")
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class InfoVO implements Serializable {

        @Schema(description = "知识库 ID", example = "abc123")
        private String id;

        @Schema(description = "知识库名称", example = "my_dataset")
        private String name;

        @Schema(description = "知识库头像 (Base64 编码)", example = "")
        private String avatar;

        @Schema(description = "租户 ID", example = "tenant_001")
        @JsonProperty("tenant_id")
        private String tenantId;

        @Schema(description = "知识库描述", example = "用于存储产品文档")
        private String description;

        @Schema(description = "嵌入模型名称", example = "BAAI/bge-large-zh-v1.5")
        @JsonProperty("embedding_model")
        private String embeddingModel;

        @Schema(description = "权限设置: me / team", example = "me")
        private String permission;

        @Schema(description = "分块方法", example = "naive")
        @JsonProperty("chunk_method")
        private String chunkMethod;

        @Schema(description = "解析器配置")
        @JsonProperty("parser_config")
        private ParserConfig parserConfig;

        @Schema(description = "分块总数", example = "1024")
        @JsonProperty("chunk_count")
        private Long chunkCount;

        @Schema(description = "文档总数", example = "50")
        @JsonProperty("document_count")
        private Long documentCount;

        @Schema(description = "创建时间 (时间戳)", example = "1700000000000")
        @JsonProperty("create_time")
        private Long createTime;

        @Schema(description = "更新时间 (时间戳)", example = "1700000001000")
        @JsonProperty("update_time")
        private Long updateTime;

        @Schema(description = "总 Token 数", example = "102400")
        @JsonProperty("token_num")
        private Long tokenNum;

        @Schema(description = "创建日期 (格式: yyyy-MM-dd HH:mm:ss)")
        @JsonProperty("create_date")
        private String createDate;

        @Schema(description = "最后更新日期 (格式: yyyy-MM-dd HH:mm:ss)")
        @JsonProperty("update_date")
        private String updateDate;
    }

    /**
     * 批量操作响应 VO
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    @Schema(description = "批量操作响应 VO")
    public static class BatchOperationVO implements Serializable {

        @Schema(description = "成功操作数量", example = "5")
        @JsonProperty("success_count")
        private Integer successCount;

        @Schema(description = "错误列表")
        private List<Object> errors;
    }

    // ========== 知识图谱相关 ==========

    /**
     * 知识图谱数据 VO (映射接口 5: knowledge_graph)
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    @Schema(description = "知识图谱数据 VO")
    public static class GraphVO implements Serializable {

        @Schema(description = "图谱节点列表")
        private List<Node> nodes;

        @Schema(description = "图谱边列表")
        private List<Edge> edges;

        @Schema(description = "思维导图数据")
        @JsonProperty("mind_map")
        private Map<String, Object> mindMap;

        /**
         * 图谱节点
         */
        @Data
        @NoArgsConstructor
        @AllArgsConstructor
        @Builder
        @Schema(description = "图谱节点")
        @JsonIgnoreProperties(ignoreUnknown = true)
        public static class Node implements Serializable {

            @Schema(description = "节点 ID", example = "node_001")
            private String id;

            @Schema(description = "节点标签", example = "产品")
            private String label;

            @Schema(description = "PageRank 值", example = "0.85")
            private Double pagerank;

            @Schema(description = "节点颜色", example = "#FF5733")
            private String color;

            @Schema(description = "节点图片 URL", example = "https://example.com/icon.png")
            private String img;
        }

        /**
         * 图谱边
         */
        @Data
        @NoArgsConstructor
        @AllArgsConstructor
        @Builder
        @Schema(description = "图谱边")
        @JsonIgnoreProperties(ignoreUnknown = true)
        public static class Edge implements Serializable {

            @Schema(description = "源节点 ID", example = "node_001")
            private String source;

            @Schema(description = "目标节点 ID", example = "node_002")
            private String target;

            @Schema(description = "边权重", example = "0.75")
            private Double weight;

            @Schema(description = "边标签 (关系描述)", example = "属于")
            private String label;
        }
    }

    // ========== 异步任务追踪 (GraphRAG/RAPTOR) ==========

    /**
     * 异步任务追踪 VO (映射接口 9/10: 任务进度返回)
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    @Schema(description = "异步任务追踪 VO")
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class TaskTraceVO implements Serializable {

        @Schema(description = "任务 ID", example = "task_001")
        private String id;

        @Schema(description = "文档 ID", example = "doc_001")
        @JsonProperty("doc_id")
        private String docId;

        @Schema(description = "起始页码", example = "1")
        @JsonProperty("from_page")
        private Integer fromPage;

        @Schema(description = "结束页码", example = "10")
        @JsonProperty("to_page")
        private Integer toPage;

        @Schema(description = "进度百分比 (0.0 - 1.0)", example = "0.75")
        private Double progress;

        @Schema(description = "进度消息", example = "正在处理第 5 页...")
        @JsonProperty("progress_msg")
        private String progressMsg;

        @Schema(description = "创建时间 (时间戳)", example = "1700000000000")
        @JsonProperty("create_time")
        private Long createTime;

        @Schema(description = "更新时间 (时间戳)", example = "1700000001000")
        @JsonProperty("update_time")
        private Long updateTime;
    }
}
