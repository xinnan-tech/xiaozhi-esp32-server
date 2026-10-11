package xiaozhi.modules.agent.vo;

import java.util.Date;
import java.util.List;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import xiaozhi.modules.agent.dto.AgentSnapshotDataDTO;

@Data
@Schema(description = "Agent config snapshot")
public class AgentSnapshotVO {
    private String id;
    private String agentId;
    @Schema(description = "Owner user ID, indicating the Agent owner of this snapshot")
    private Long userId;
    private Integer versionNo;
    private List<String> changedFields;
    private List<String> fieldOrder;
    private String source;
    @Schema(description = "Restore source snapshot ID; only set for restored result versions")
    private String restoreFromSnapshotId;
    @Schema(description = "Restore source version number, only restore if result version has value")
    private Integer restoreFromVersionNo;
    @Schema(description = "Creator, indicating the operator who triggered this snapshot write")
    private Long creator;
    private Date createdAt;
    private AgentSnapshotDataDTO snapshotData;
    private AgentSnapshotDataDTO afterSnapshotData;
    @Schema(description = "Restore desensitized current config for preview; only populated in detail API")
    private AgentSnapshotDataDTO currentSnapshotData;
    @Schema(description = "Fingerprint of current config state corresponding to restore preview, only present in detail API")
    private String currentStateToken;
}
