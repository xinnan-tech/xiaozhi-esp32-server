package xiaozhi.modules.agent.service;

import java.util.List;

import com.baomidou.mybatisplus.extension.service.IService;

import xiaozhi.modules.agent.entity.AgentPluginMapping;

/**
 * @description 针对表【ai_agent_plugin_mapping(Agent与插件的唯一映射表)】的数据库操作Service
 * @createDate 2025-05-25 22:33:17
 */
public interface AgentPluginMappingService extends IService<AgentPluginMapping> {

    /**
     * 根据智能体id获取插件参数
     * 
     * @param agentId
     * @return
     */
    List<AgentPluginMapping> agentPluginParamsByAgentId(String agentId);

    /**
     * 根据智能体id删除插件参数
     * 
     * @param agentId
     */
    void deleteByAgentId(String agentId);
}
