package xiaozhi.modules.correctword.entity;

import java.util.Date;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
@TableName("ai_agent_correct_word_file")
@Schema(description = "Agent replacement word file")
public class CorrectWordFileEntity {

    @TableId(type = IdType.ASSIGN_UUID)
    @Schema(description = "Replacement word file ID")
    private String id;

    @Schema(description = "Original filename")
    private String fileName;

    @Schema(description = "Replacement word count")
    private Integer wordCount;

    @Schema(description = "Original file content (for download)")
    private String content;

    @Schema(description = "Creator")
    private Long creator;

    @Schema(description = "Creation Time")
    private Date createdAt;

    @Schema(description = "Updated by")
    private Long updater;

    @Schema(description = "Update time")
    private Date updatedAt;
}
