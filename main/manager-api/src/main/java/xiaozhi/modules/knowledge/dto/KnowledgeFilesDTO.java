package xiaozhi.modules.knowledge.dto;

import java.io.Serial;
import java.io.Serializable;
import java.util.Date;
import java.util.Map;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
@Schema(description = "知识库文档")
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

    @Schema(description = "元数据字段")
    private Map<String, Object> metaFields;

    @Schema(description = "分块方法")
    private String chunkMethod;

    @Schema(description = "解析器配置")
    private Map<String, Object> parserConfig;

    @Schema(description = "状态")
    private Integer status;

    @Schema(description = "文档解析状态")
    private String run;

    @Schema(description = "创建者")
    private Long creator;

    @Schema(description = "创建时间")
    private Date createdAt;

    @Schema(description = "更新者")
    private Long updater;

    @Schema(description = "更新时间")
    private Date updatedAt;

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

        // 根据run字段的值直接映射到对应的状态码
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