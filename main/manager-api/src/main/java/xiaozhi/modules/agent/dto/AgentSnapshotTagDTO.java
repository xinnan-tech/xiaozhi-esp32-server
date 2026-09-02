package xiaozhi.modules.agent.dto;

import java.io.Serializable;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
@Schema(description = "智能体快照标签")
public class AgentSnapshotTagDTO implements Serializable {
    private static final long serialVersionUID = 1L;

    private String id;
    private String tagName;
    private Integer sort;
}
