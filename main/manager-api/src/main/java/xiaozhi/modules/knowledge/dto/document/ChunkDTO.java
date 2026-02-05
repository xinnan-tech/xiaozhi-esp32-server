package xiaozhi.modules.knowledge.dto.document;

import lombok.*;
import io.swagger.v3.oas.annotations.media.Schema;
import java.io.Serializable;
import java.util.List;
import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.*;

/**
 * 切片管理聚合 DTO
 */
@Schema(description = "切片管理聚合 DTO")
public class ChunkDTO {

    /**
     * 新增切片请求参数
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "新增切片请求参数")
    public static class AddReq implements Serializable {
        private static final long serialVersionUID = 1L;

        @Schema(description = "切片内容", requiredMode = Schema.RequiredMode.REQUIRED)
        @NotBlank(message = "切片内容不能为空")
        private String content;

        @Schema(description = "重要关键词列表")
        @JsonProperty("important_keywords")
        private List<String> importantKeywords;

        @Schema(description = "预设问题列表")
        private List<String> questions;
    }

    /**
     * 更新切片请求参数
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "更新切片请求参数")
    public static class UpdateReq implements Serializable {
        private static final long serialVersionUID = 1L;

        @Schema(description = "新的切片内容")
        private String content;

        @Schema(description = "更新关键词列表 (覆盖原有列表)")
        @JsonProperty("important_keywords")
        private List<String> importantKeywords;

        @Schema(description = "启用/禁用 (true: 启用, false: 禁用)")
        private Boolean available;
    }

    /**
     * 获取切片列表请求参数
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "获取切片列表请求参数")
    public static class ListReq implements Serializable {
        private static final long serialVersionUID = 1L;

        @Schema(description = "页码 (默认 1)")
        private Integer page;

        @Schema(description = "每页数量 (默认 30)")
        @JsonProperty("page_size")
        private Integer pageSize;

        @Schema(description = "搜索关键词 (全文检索)")
        private String keywords;

        @Schema(description = "精确切片 ID")
        private String id;
    }

    /**
     * 批量删除切片请求参数
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "批量删除切片请求参数")
    public static class RemoveReq implements Serializable {
        private static final long serialVersionUID = 1L;

        @Schema(description = "切片 ID 列表", requiredMode = Schema.RequiredMode.REQUIRED)
        @JsonProperty("chunk_ids")
        @NotEmpty(message = "切片ID列表不能为空")
        private List<String> chunkIds;
    }

    /**
     * 文档切片信息 VO
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "文档切片信息")
    public static class InfoVO implements Serializable {
        private static final long serialVersionUID = 1L;

        @Schema(description = "切片 ID (通常为 document_id + 索引)", requiredMode = Schema.RequiredMode.REQUIRED)
        private String id;

        @Schema(description = "切片文本内容 (全文检索的主要对象)", requiredMode = Schema.RequiredMode.REQUIRED)
        private String content;

        @Schema(description = "所属文档 ID", requiredMode = Schema.RequiredMode.REQUIRED)
        @JsonProperty("document_id")
        private String documentId;

        @Schema(description = "文档名称 / 关键词")
        @JsonProperty("docnm_kwd")
        private String docnmKwd;

        @Schema(description = "重要关键词列表 (用于关键词增强检索)")
        @JsonProperty("important_keywords")
        private List<String> importantKeywords;

        @Schema(description = "预设问题列表 (用于 Q&A 模式增强)")
        private List<String> questions;

        @Schema(description = "关联的图片 ID")
        @JsonProperty("image_id")
        private String imageId;

        @Schema(description = "所属知识库 ID")
        @JsonProperty("dataset_id")
        private String datasetId;

        @Schema(description = "切片是否可用 (true: 参与检索, false: 被禁用)")
        private Boolean available;

        @Schema(description = "切片在原文中的位置索引列表")
        private List<Integer> positions;
    }

    /**
     * 分片列表聚合响应
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "分片列表聚合响应")
    public static class ListVO implements Serializable {
        private static final long serialVersionUID = 1L;

        @Schema(description = "切片信息列表")
        private List<InfoVO> chunks;

        @Schema(description = "关联的文档详细信息")
        private DocumentDTO.InfoVO doc;

        @Schema(description = "总记录数")
        private Long total;
    }
}
