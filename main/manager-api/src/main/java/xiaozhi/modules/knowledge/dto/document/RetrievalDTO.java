package xiaozhi.modules.knowledge.dto.document;

import lombok.*;
import io.swagger.v3.oas.annotations.media.Schema;
import java.io.Serializable;
import java.util.List;
import java.util.Map;
import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.*;

/**
 * 检索与元数据管理聚合 DTO
 */
@Schema(description = "检索与元数据管理聚合 DTO")
public class RetrievalDTO {

    /**
     * 文档聚合信息 (VO)
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "文档聚合信息")
    public static class DocAggVO implements Serializable {
        private static final long serialVersionUID = 1L;

        @Schema(description = "文档名称")
        @JsonProperty("doc_name")
        private String docName;

        @Schema(description = "文档 ID")
        @JsonProperty("doc_id")
        private String docId;

        @Schema(description = "数量")
        private Integer count;
    }

    /**
     * 检索测试请求参数
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "检索测试请求参数")
    public static class TestReq implements Serializable {
        private static final long serialVersionUID = 1L;

        @Schema(description = "知识库 ID 列表", requiredMode = Schema.RequiredMode.REQUIRED)
        @JsonProperty("dataset_ids")
        @NotEmpty(message = "知识库ID列表不能为空")
        private List<String> datasetIds;

        @Schema(description = "检索问题", requiredMode = Schema.RequiredMode.REQUIRED)
        @NotBlank(message = "检索问题不能为空")
        private String question;

        @Schema(description = "相似度阈值 (默认 0.2)")
        @JsonProperty("similarity_threshold")
        private Float similarityThreshold;

        @Schema(description = "向量相似度权重 (默认 0.3)")
        @JsonProperty("vector_similarity_weight")
        private Float vectorSimilarityWeight;

        @Schema(description = "返回 Top K 切片 (默认 1024)")
        @JsonProperty("top_k")
        private Integer topK;

        @Schema(description = "重排序模型 ID")
        @JsonProperty("rerank_id")
        private String rerankId;

        @Schema(description = "是否高亮关键词")
        private Boolean highlight;

        @Schema(description = "是否启用关键词检索")
        private Boolean keyword;
    }

    /**
     * 检索命中结果 (VO)
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "检索命中切片详情")
    public static class HitVO implements Serializable {
        private static final long serialVersionUID = 1L;

        @Schema(description = "切片 ID", requiredMode = Schema.RequiredMode.REQUIRED)
        private String id;

        @Schema(description = "切片内容", requiredMode = Schema.RequiredMode.REQUIRED)
        private String content;

        @Schema(description = "所属文档 ID", requiredMode = Schema.RequiredMode.REQUIRED)
        @JsonProperty("document_id")
        private String documentId;

        @Schema(description = "所属知识库 ID")
        @JsonProperty("dataset_id")
        private String datasetId;

        @Schema(description = "文档名称")
        @JsonProperty("document_name")
        private String documentName;

        @Schema(description = "文档关键词")
        @JsonProperty("document_keyword")
        private String documentKeyword;

        @Schema(description = "综合相似度", requiredMode = Schema.RequiredMode.REQUIRED)
        private Float similarity;

        @Schema(description = "向量相似度")
        @JsonProperty("vector_similarity")
        private Float vectorSimilarity;

        @Schema(description = "关键词相似度")
        @JsonProperty("term_similarity")
        private Float termSimilarity;

        @Schema(description = "索引位置")
        private Integer index;

        @Schema(description = "高亮内容")
        private String highlight;

        @Schema(description = "重要关键词列表")
        @JsonProperty("important_keywords")
        private List<String> importantKeywords;

        @Schema(description = "预设问题列表")
        private List<String> questions;

        @Schema(description = "图片 ID")
        @JsonProperty("image_id")
        private String imageId;

        @Schema(description = "位置索引")
        private List<Integer> positions;
    }

    /**
     * 知识库元数据摘要 (VO)
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "知识库元数据摘要信息")
    public static class MetaSummaryVO implements Serializable {
        private static final long serialVersionUID = 1L;

        @Schema(description = "文档总数", requiredMode = Schema.RequiredMode.REQUIRED)
        @JsonProperty("total_doc_count")
        private Long totalDocCount;

        @Schema(description = "Token 总数", requiredMode = Schema.RequiredMode.REQUIRED)
        @JsonProperty("total_token_count")
        private Long totalTokenCount;

        @Schema(description = "文件类型分布 (key: 文件后缀, value: 数量)")
        @JsonProperty("file_type_distribution")
        private Map<String, Long> fileTypeDistribution;

        @Schema(description = "文状态分布 (key: 状态码, value: 数量)")
        @JsonProperty("status_distribution")
        private Map<String, Long> statusDistribution;

        @Schema(description = "自定义元数据统计 (key: 字段名, value: 数量/值)")
        @JsonProperty("custom_metadata")
        private Map<String, Object> customMetadata;
    }

    /**
     * 批量更新元数据请求参数
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "批量更新元数据请求参数")
    public static class MetaBatchReq implements Serializable {
        private static final long serialVersionUID = 1L;

        @Schema(description = "筛选器: 用于指定要更新的文档范围 (默认全部)")
        private Selector selector;

        @Schema(description = "新增或更新的元数据列表")
        private List<UpdateItem> updates;

        @Schema(description = "需要删除的元数据键列表")
        private List<DeleteItem> deletes;

        /**
         * 文档筛选器
         */
        @Data
        @Builder
        @NoArgsConstructor
        @AllArgsConstructor
        @Schema(description = "元数据更新筛选器")
        public static class Selector implements Serializable {
            private static final long serialVersionUID = 1L;

            @Schema(description = "指定文档 ID 列表")
            @JsonProperty("document_ids")
            private List<String> documentIds;

            @Schema(description = "元数据条件匹配 (key: 字段名, value: 匹配值)")
            @JsonProperty("metadata_condition")
            private Map<String, Object> metadataCondition;
        }

        /**
         * 更新项
         */
        @Data
        @Builder
        @NoArgsConstructor
        @AllArgsConstructor
        @Schema(description = "元数据更新项")
        public static class UpdateItem implements Serializable {
            private static final long serialVersionUID = 1L;

            @Schema(description = "元数据键名", requiredMode = Schema.RequiredMode.REQUIRED)
            private String key;

            @Schema(description = "元数据值", requiredMode = Schema.RequiredMode.REQUIRED)
            private Object value;
        }

        /**
         * 删除项
         */
        @Data
        @Builder
        @NoArgsConstructor
        @AllArgsConstructor
        @Schema(description = "元数据删除项")
        public static class DeleteItem implements Serializable {
            private static final long serialVersionUID = 1L;

            @Schema(description = "需删除的元数据键名", requiredMode = Schema.RequiredMode.REQUIRED)
            private String key;
        }
    }

    /**
     * 召回测试结果聚合响应
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "召回测试结果聚合响应")
    public static class ResultVO implements Serializable {
        private static final long serialVersionUID = 1L;

        @Schema(description = "检索命中的切片列表")
        private List<HitVO> chunks;

        @Schema(description = "文档分布统计")
        @JsonProperty("doc_aggs")
        private List<DocAggVO> docAggs;

        @Schema(description = "总命中记录数")
        private Long total;
    }
}
