package xiaozhi.modules.knowledge.entity;

import java.util.Date;

import com.baomidou.mybatisplus.annotation.FieldFill;
import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
@TableName(value = "ai_rag_dataset", autoResultMap = true)
@Schema(description = "知识库知识库表")
public class KnowledgeBaseEntity {

    @TableId(type = IdType.ASSIGN_UUID)
    @Schema(description = "唯一标识")
    private String id;

    @Schema(description = "知识库ID")
    private String datasetId;

    @Deprecated
    @Schema(description = "RAG模型配置ID (连接RAGFlow的凭证指针)")
    private String ragModelId;

    @Schema(description = "租户ID")
    private String tenantId;

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

    @Schema(description = "文档总数")
    private Long documentCount;

    @Schema(description = "总Token数")
    private Long tokenNum;

    @Schema(description = "状态(0:禁用 1:启用)")
    private Integer status;

    @Schema(description = "创建者")
    @TableField(fill = FieldFill.INSERT)
    private Long creator;

    @Schema(description = "创建时间")
    @TableField(fill = FieldFill.INSERT)
    private Date createdAt;

    @Schema(description = "更新者")
    @TableField(fill = FieldFill.UPDATE)
    private Long updater;

    @Schema(description = "更新时间")
    @TableField(fill = FieldFill.UPDATE)
    private Date updatedAt;
}