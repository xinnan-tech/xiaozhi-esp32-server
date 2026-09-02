package xiaozhi.modules.correctword.vo;

import java.util.Date;
import java.util.List;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
@Schema(description = "替换词文件列表VO")
public class CorrectWordFileVO {

    @Schema(description = "替换词文件ID")
    private String id;

    @Schema(description = "原始文件名")
    private String fileName;

    @Schema(description = "替换词数量")
    private Integer wordCount;

    @Schema(description = "替换词内容，每行一条")
    private List<String> content;

    @Schema(description = "创建时间")
    private Date createdAt;

    @Schema(description = "更新时间")
    private Date updatedAt;
}
