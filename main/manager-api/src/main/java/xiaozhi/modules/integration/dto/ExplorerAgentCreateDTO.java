package xiaozhi.modules.integration.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class ExplorerAgentCreateDTO {
    @NotBlank
    private String agentName;
}
