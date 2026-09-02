package xiaozhi.modules.agent.vo;

import java.util.Date;
import java.util.List;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import xiaozhi.modules.agent.dto.AgentSnapshotDataDTO;

@Data
@Schema(description = "智能体配置快照")
public class AgentSnapshotVO {
    private String id;
    private String agentId;
    @Schema(description = "所属用户ID，表示该快照归属的智能体所有者")
    private Long userId;
    private Integer versionNo;
    private List<String> changedFields;
    private List<String> fieldOrder;
    private String source;
    @Schema(description = "恢复来源快照ID，仅恢复结果版本有值")
    private String restoreFromSnapshotId;
    @Schema(description = "恢复来源版本号，仅恢复结果版本有值")
    private Integer restoreFromVersionNo;
    @Schema(description = "创建者，表示触发本次快照写入的操作人")
    private Long creator;
    private Date createdAt;
    private AgentSnapshotDataDTO snapshotData;
    private AgentSnapshotDataDTO afterSnapshotData;
    @Schema(description = "恢复预览对应的脱敏当前配置，仅详情接口有值")
    private AgentSnapshotDataDTO currentSnapshotData;
    @Schema(description = "恢复预览对应的当前配置状态指纹，仅详情接口有值")
    private String currentStateToken;
}
