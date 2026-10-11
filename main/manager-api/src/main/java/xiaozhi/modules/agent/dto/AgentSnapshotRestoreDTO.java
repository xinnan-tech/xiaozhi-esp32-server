package xiaozhi.modules.agent.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
@Schema(description = "智能体快照恢复请求")
public class AgentSnapshotRestoreDTO {
    @NotBlank
    @Schema(description = "预览时由服务端生成的当前配置状态指纹")
    private String currentStateToken;
}
