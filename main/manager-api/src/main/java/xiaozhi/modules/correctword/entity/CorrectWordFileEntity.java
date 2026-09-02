package xiaozhi.modules.correctword.entity;

import java.util.Date;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
@TableName("ai_agent_correct_word_file")
@Schema(description = "智能体替换词文件")
public class CorrectWordFileEntity {

    @TableId(type = IdType.ASSIGN_UUID)
    @Schema(description = "替换词文件ID")
    private String id;

    @Schema(description = "原始文件名")
    private String fileName;

    @Schema(description = "替换词数量")
    private Integer wordCount;

    @Schema(description = "文件原始内容（用于下载）")
    private String content;

    @Schema(description = "创建者")
    private Long creator;

    @Schema(description = "创建时间")
    private Date createdAt;

    @Schema(description = "更新者")
    private Long updater;

    @Schema(description = "更新时间")
    private Date updatedAt;
}
