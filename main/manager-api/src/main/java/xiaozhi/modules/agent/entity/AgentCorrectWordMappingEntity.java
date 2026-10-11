package xiaozhi.modules.agent.entity;

import java.util.Date;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
@TableName("ai_agent_correct_word_mapping")
@Schema(description = "Agent replacement word file association")
public class AgentCorrectWordMappingEntity {

    @TableId(type = IdType.ASSIGN_UUID)
    @Schema(description = "Primary key")
    private String id;

    @Schema(description = "Agent ID")
    private String agentId;

    @Schema(description = "Replacement word file ID")
    private String fileId;

    @Schema(description = "Creator")
    private Long creator;

    @Schema(description = "Creation Time")
    private Date createdAt;

    @Schema(description = "Updated by")
    private Long updater;

    @Schema(description = "Update time")
    private Date updatedAt;
}
