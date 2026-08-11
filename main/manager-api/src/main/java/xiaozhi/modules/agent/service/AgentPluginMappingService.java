package xiaozhi.modules.agent.service;

import java.util.List;
import java.util.Map;

import com.baomidou.mybatisplus.extension.repository.IRepository;

import xiaozhi.modules.agent.entity.AgentPluginMapping;

/**
 * @description 针对表【ai_agent_plugin_mapping(Agent与插件的唯一映射表)】的数据库操作Service
 * @createDate 2025-05-25 22:33:17
 */
public interface AgentPluginMappingService extends IRepository<AgentPluginMapping> {

    /**
     * 根据智能体id获取插件参数
     *
     * @param agentId
     * @return
     */
    List<AgentPluginMapping> agentPluginParamsByAgentId(String agentId);

    Map<String, Object> prepareParamsForStorage(String agentId, String pluginId,
            Map<String, Object> submittedParams, String existingParamInfo);

    void redactCredentialsForAdmin(List<AgentPluginMapping> mappings);

    String resolveParamsForServer(AgentPluginMapping mapping);

    /**
     * 根据智能体id删除插件参数
     *
     * @param agentId
     */
    void deleteByAgentId(String agentId);

    /**
     * 根据插件ID删除所有智能体的插件映射
     *
     * @param pluginId 插件ID
     */
    void deleteByPluginId(String pluginId);
}
