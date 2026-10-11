package xiaozhi.modules.agent.service;

import java.util.List;

import com.baomidou.mybatisplus.extension.repository.IRepository;

import xiaozhi.modules.agent.entity.AgentPluginMapping;

/**
 * @description Database operation Service for table [ai_agent_plugin_mapping (Unique mapping between Agent and Plugin)]
 * @createDate 2025-05-25 22:33:17
 */
public interface AgentPluginMappingService extends IRepository<AgentPluginMapping> {

    /**
     * Get plugin parameters by agent ID
     *
     * @param agentId
     * @return
     */
    List<AgentPluginMapping> agentPluginParamsByAgentId(String agentId);

    /**
     * Delete plugin parameters by agent ID
     *
     * @param agentId
     */
    void deleteByAgentId(String agentId);

    /**
     * Delete plugin mappings for all Agents by plugin ID
     *
     * @param pluginId Plugin ID
     */
    void deleteByPluginId(String pluginId);
}
