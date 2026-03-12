package xiaozhi.modules.knowledge.dto;

import java.io.Serializable;
import java.util.Date;
import java.util.Map;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

/**
 * 文档 DTO
 */
@Data
@Schema(description = "知识库文档")
public class DocumentDTO implements Serializable {
    private static final long serialVersionUID = 1L;

    @Schema(description = "本地ID")
    private String id;

    @Schema(description = "知识库ID")
    private String datasetId;

    @Schema(description = "RAGFlow文档ID")
    private String documentId;

    @Schema(description = "文档名称")
    private String name;

    @Schema(description = "文件大小")
    private Long size;

    @Schema(description = "文件类型")
    private String type;

    @Schema(description = "分块方法")
    private String chunkMethod;

    @Schema(description = "解析配置")
    private Map<String, Object> parserConfig;

    @Schema(description = "处理状态 (1:解析中 3:成功 4:失败)")
    private Integer status;

    @Schema(description = "错误信息")
    private String error;

    @Schema(description = "分块数量")
    private Integer chunkCount;

    @Schema(description = "Token数量")
    private Long tokenCount;

    @Schema(description = "是否启用")
    private Integer enabled;

    @Schema(description = "创建时间")
    private Date createdAt;

    @Schema(description = "更新时间")
    private Date updatedAt;

    @Schema(description = "上传进度 (虚拟字段)")
    private Double progress;

    @Schema(description = "缩略图/预览图 (虚拟字段)")
    private String thumbnail;
}
