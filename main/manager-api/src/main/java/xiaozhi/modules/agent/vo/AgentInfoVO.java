package xiaozhi.modules.agent.vo;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import lombok.EqualsAndHashCode;
import xiaozhi.modules.agent.dto.ContextProviderDTO;
import xiaozhi.modules.agent.entity.AgentEntity;
import xiaozhi.modules.agent.entity.AgentPluginMapping;

import java.util.List;

/**
 * Agent信息返回体VO
 * 这里直接extend了Agent实体类AgentEntity，后续需要规范返回字段可以copy字段出来
 */
@EqualsAndHashCode(callSuper = true)
@Data
public class AgentInfoVO extends AgentEntity
{
    @Schema(description = "插件列表Id")
    private List<AgentPluginMapping> functions;

    @Schema(description = "上下文源配置")
    private List<ContextProviderDTO> contextProviders;

    @Schema(description = "替换词文件ID列表")
    private List<String> correctWordFileIds;

    @Schema(description = "当前配置版本号")
    private Integer currentVersionNo;
}
