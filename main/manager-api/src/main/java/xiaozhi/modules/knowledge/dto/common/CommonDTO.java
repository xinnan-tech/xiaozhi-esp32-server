package xiaozhi.modules.knowledge.dto.common;

import lombok.*;
import io.swagger.v3.oas.annotations.media.Schema;
import java.io.Serializable;
import java.util.List;
import java.util.Map;
import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.*;

@Schema(description = "通用扩展功能 DTO")
public class CommonDTO {

    // ========== 1. 引用详情 (detail_share_embedded) ==========

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "引用详情请求")
    public static class ReferenceDetailReq implements Serializable {
        @Schema(description = "切片 ID", requiredMode = Schema.RequiredMode.REQUIRED)
        @NotBlank(message = "切片 ID 不能为空")
        @JsonProperty("chunk_id")
        private String chunkId;

        @Schema(description = "知识库 ID")
        @JsonProperty("knowledge_id")
        private String knowledgeId;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "引用详情响应")
    public static class ReferenceDetailVO implements Serializable {
        @Schema(description = "切片 ID")
        @JsonProperty("chunk_id")
        private String chunkId;

        @Schema(description = "完整内容")
        @JsonProperty("content_with_weight")
        private String contentWithWeight;

        @Schema(description = "文档名称")
        @JsonProperty("doc_name")
        private String docName;

        @Schema(description = "图片 ID 列表")
        @JsonProperty("img_id")
        private String imageId; // 注意：RAGFlow 有时返回 String 有时返回 List，需根据实际情况确认，暂定 String 用于 ID

        @Schema(description = "文档 ID")
        @JsonProperty("doc_id")
        private String docId;
    }

    // ========== 2. 通用问答 (ask_about) - 调试用 ==========

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    @Schema(description = "通用问答请求 (调试用)")
    public static class AskAboutReq implements Serializable {
        @Schema(description = "用户问题", requiredMode = Schema.RequiredMode.REQUIRED, example = "What is this dataset about?")
        @NotBlank(message = "问题不能为空")
        @JsonProperty("question")
        private String question;

        @Schema(description = "数据集 ID 列表", requiredMode = Schema.RequiredMode.REQUIRED)
        @NotEmpty(message = "数据集列表不能为空")
        @JsonProperty("dataset_ids")
        private List<String> datasetIds;
    }

    // 响应通常复用 String 或者简单的 Map 结构，视具体实现而定，暂不定义专用 VO
}
