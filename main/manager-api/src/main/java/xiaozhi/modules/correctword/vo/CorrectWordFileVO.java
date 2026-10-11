package xiaozhi.modules.correctword.vo;

import java.util.Date;
import java.util.List;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
@Schema(description = "Replacement word file list VO")
public class CorrectWordFileVO {

    @Schema(description = "Replacement word file ID")
    private String id;

    @Schema(description = "Original filename")
    private String fileName;

    @Schema(description = "Replacement word count")
    private Integer wordCount;

    @Schema(description = "Replacement word content, one per line")
    private List<String> content;

    @Schema(description = "Creation Time")
    private Date createdAt;

    @Schema(description = "Update time")
    private Date updatedAt;
}
