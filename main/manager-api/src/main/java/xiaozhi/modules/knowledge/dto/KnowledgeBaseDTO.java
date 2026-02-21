package xiaozhi.modules.knowledge.dto;

import java.io.Serial;
import java.io.Serializable;
import java.util.Date;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
@Schema(description = "知识库知识库")
public class KnowledgeBaseDTO implements Serializable {

    @Serial
    private static final long serialVersionUID = 1L;

    @Schema(description = "唯一标识")
    private String id;

    @Schema(description = "知识库ID")
    private String datasetId;

    @Schema(description = "RAG模型配置ID")
    private String ragModelId;

    @Schema(description = "知识库名称")
    private String name;

    @Schema(description = "知识库头像(Base64)")
    private String avatar;

    @Schema(description = "知识库描述")
    private String description;

    @Schema(description = "嵌入模型名称")
    private String embeddingModel;

    @Schema(description = "权限设置: me/team")
    private String permission;

    @Schema(description = "分块方法")
    private String chunkMethod;

    @Schema(description = "解析器配置(JSON String)")
    private String parserConfig;

    @Schema(description = "分块总数")
    private Long chunkCount;

    @Schema(description = "总Token数")
    private Long tokenNum;

    @Schema(description = "状态(0:禁用 1:启用)")
    private Integer status;

    @Schema(description = "创建者")
    private Long creator;

    @Schema(description = "创建时间")
    private Date createdAt;

    @Schema(description = "更新者")
    private Long updater;

    @Schema(description = "更新时间")
    private Date updatedAt;

    @Schema(description = "文档数量")
    private Integer documentCount;
}