package xiaozhi.modules.agent.dto;

import java.io.Serializable;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

/**
 * Agent memory update DTO
 */
@Data
@Schema(description = "Agent memory update object")
public class AgentMemoryDTO implements Serializable {
    private static final long serialVersionUID = 1L;

    @Schema(description = "Summary memory", example = "Build a growing dynamic memory network that retains key information in limited space while intelligently maintaining information evolution trajectory\n" +
            "Summarize important user information based on conversation records to provide more personalized service in future conversations", required = false)
    private String summaryMemory;
}
