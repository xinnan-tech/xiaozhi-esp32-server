package xiaozhi.modules.knowledge.entity;

import java.io.Serializable;
import java.util.Date;

import com.baomidou.mybatisplus.annotation.FieldFill;
import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

/**
 * 文档表 (Shadow DB for RAGFlow Documents)
 * 对应表名: ai_knowledge_document
 */
@Data
@TableName(value = "ai_rag_knowledge_document", autoResultMap = true)
@Schema(description = "知识库文档表")
public class DocumentEntity implements Serializable {
    private static final long serialVersionUID = 1L;

    @TableId(type = IdType.ASSIGN_UUID)
    @Schema(description = "本地唯一ID")
    private String id;

    @Schema(description = "知识库ID (关联 ai_rag_dataset.dataset_id)")
    private String datasetId;

    @Schema(description = "RAGFlow文档ID (远程ID)")
    private String documentId;

    @Schema(description = "文档名称")
    private String name;

    @Schema(description = "文件大小(Bytes)")
    private Long size;

    @Schema(description = "文件类型(pdf/doc/txt等)")
    private String type;

    @Schema(description = "分块方法")
    private String chunkMethod;

    @Schema(description = "解析配置(JSON String)")
    private String parserConfig;

    @Schema(description = "处理状态 (0:未开始 1:解析中 2:取消 3:成功 4:失败)")
    private Integer status;

    @Schema(description = "解析错误信息")
    private String error;

    @Schema(description = "分块数量")
    private Integer chunkCount;

    @Schema(description = "Token数量")
    private Long tokenCount;

    @Schema(description = "是否启用 (0:禁用 1:启用)")
    private Integer enabled;

    @Schema(description = "创建者")
    @TableField(fill = FieldFill.INSERT)
    private Long creator;

    @Schema(description = "创建时间")
    @TableField(fill = FieldFill.INSERT)
    private Date createdAt;

    @Schema(description = "更新时间")
    @TableField(fill = FieldFill.UPDATE)
    private Date updatedAt;

    @Schema(description = "最新同步时间")
    private Date lastSyncAt;
}
