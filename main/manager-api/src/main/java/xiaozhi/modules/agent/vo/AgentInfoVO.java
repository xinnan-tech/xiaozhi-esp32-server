package xiaozhi.modules.agent.vo;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import lombok.EqualsAndHashCode;
import xiaozhi.modules.agent.dto.ContextProviderDTO;
import xiaozhi.modules.agent.entity.AgentEntity;
import xiaozhi.modules.agent.entity.AgentPluginMapping;

import java.util.List;

/**
 * Agent information response body VO
 * This directly extends the Agent entity class AgentEntity, fields can be copied out later if return fields need to be standardized
 */
@EqualsAndHashCode(callSuper = true)
@Data
public class AgentInfoVO extends AgentEntity
{
    @Schema(description = "Plugin list ID")
    private List<AgentPluginMapping> functions;

    @Schema(description = "Context-provider configuration")
    private List<ContextProviderDTO> contextProviders;

    @Schema(description = "List of replacement word file IDs")
    private List<String> correctWordFileIds;

    @Schema(description = "Current config version")
    private Integer currentVersionNo;
}
