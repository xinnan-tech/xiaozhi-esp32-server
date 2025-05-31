package xiaozhi.modules.agent.service;

import xiaozhi.modules.agent.entity.AgentPluginMapping;
import com.baomidou.mybatisplus.extension.service.IService;

import java.util.List;

/**
* @description 针对表【ai_agent_plugin_mapping(Agent与插件的唯一映射表)】的数据库操作Service
* @createDate 2025-05-25 22:33:17
*/
public interface AgentPluginMappingService extends IService<AgentPluginMapping> {

    List<AgentPluginMapping> agentPluginParamsByAgentId(String agentId);
}
