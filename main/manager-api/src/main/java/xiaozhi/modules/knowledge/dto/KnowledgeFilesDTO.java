package xiaozhi.modules.knowledge.dto;

import java.io.Serial;
import java.io.Serializable;
import java.util.Date;
import java.util.Map;

import io.swagger.v3.oas.annotations.media.Schema;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.Data;

@Data
@Schema(description = "知识库文档")
@JsonIgnoreProperties(ignoreUnknown = true)
public class KnowledgeFilesDTO implements Serializable {

    @Serial
    private static final long serialVersionUID = 1L;
    @Schema(description = "唯一标识")
    private String id;

    @Schema(description = "文档ID")
    private String documentId;

    @Schema(description = "知识库ID")
    private String datasetId;

    @Schema(description = "文档名称")
    private String name;

    @Schema(description = "文档类型")
    private String fileType;

    @Schema(description = "文件大小（字节）")
    private Long fileSize;

    @Schema(description = "文件路径")
    private String filePath;

    @Schema(description = "解析进度 (0.0 ~ 1.0)")
    private Double progress;

    @Schema(description = "缩略图 (Base64 或 URL)")
    private String thumbnail;

    @Schema(description = "解析耗时 (单位: 秒)")
    private Double processDuration;

    @Schema(description = "来源类型 (local, s3, url 等)")
    private String sourceType;

    @Schema(description = "元数据字段 (Map 格式)")
    private Map<String, Object> metaFields;

    @Schema(description = "分块方法")
    private String chunkMethod;

    @Schema(description = "解析器配置")
    private Map<String, Object> parserConfig;

    @Schema(description = "可用状态 (1: 启用/正常, 0: 禁用/失效)")
    private String status;

    @Schema(description = "运行状态 (UNSTART/RUNNING/CANCEL/DONE/FAIL)")
    private String run;

    @Schema(description = "创建者")
    private Long creator;

    @Schema(description = "创建时间")
    private Date createdAt;

    @Schema(description = "更新者")
    private Long updater;

    @Schema(description = "更新时间")
    private Date updatedAt;

    @Schema(description = "分块数量")
    private Integer chunkCount;

    @Schema(description = "Token数量")
    private Long tokenCount;

    @Schema(description = "解析错误信息")
    private String error;

    // 文档解析状态常量定义
    private static final Integer STATUS_UNSTART = 0;
    private static final Integer STATUS_RUNNING = 1;
    private static final Integer STATUS_CANCEL = 2;
    private static final Integer STATUS_DONE = 3;
    private static final Integer STATUS_FAIL = 4;

    /**
     * 获取文档解析状态码（基于run字段转换）
     */
    public Integer getParseStatusCode() {
        if (run == null) {
            return STATUS_UNSTART;
        }

        // RAGFlow根据run字段的值直接映射到对应的状态码
        switch (run.toUpperCase()) {
            case "RUNNING":
                return STATUS_RUNNING;
            case "CANCEL":
                return STATUS_CANCEL;
            case "DONE":
                return STATUS_DONE;
            case "FAIL":
                return STATUS_FAIL;
            case "UNSTART":
            default:
                return STATUS_UNSTART;
        }
    }

}