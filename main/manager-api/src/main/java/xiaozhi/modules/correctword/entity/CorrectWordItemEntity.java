package xiaozhi.modules.correctword.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
@TableName("ai_agent_correct_word_item")
@Schema(description = "替换词词条")
public class CorrectWordItemEntity {

    @TableId(type = IdType.ASSIGN_UUID)
    @Schema(description = "词条ID")
    private String id;

    @Schema(description = "所属文件ID")
    private String fileId;

    @Schema(description = "原词")
    private String sourceWord;

    @Schema(description = "替换词")
    private String targetWord;
}
