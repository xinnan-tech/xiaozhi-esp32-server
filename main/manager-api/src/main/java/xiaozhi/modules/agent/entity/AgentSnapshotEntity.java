package xiaozhi.modules.agent.entity;

import java.util.Date;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
@TableName("ai_agent_snapshot")
@Schema(description = "智能体配置快照")
public class AgentSnapshotEntity {

    @TableId(type = IdType.ASSIGN_UUID)
    @Schema(description = "快照ID")
    private String id;

    @Schema(description = "智能体ID")
    private String agentId;

    @Schema(description = "所属用户ID")
    private Long userId;

    @Schema(description = "版本号")
    private Integer versionNo;

    @Schema(description = "快照数据JSON")
    private String snapshotData;

    @Schema(description = "变更字段JSON")
    private String changedFields;

    @Schema(description = "快照来源")
    private String source;

    @Schema(description = "恢复来源快照ID")
    private String restoreFromSnapshotId;

    @Schema(description = "恢复来源版本号")
    private Integer restoreFromVersionNo;

    @Schema(description = "创建者")
    private Long creator;

    @Schema(description = "创建时间")
    private Date createdAt;

    @Schema(description = "快照数据脱敏规则版本")
    private Integer redactionVersion;
}
