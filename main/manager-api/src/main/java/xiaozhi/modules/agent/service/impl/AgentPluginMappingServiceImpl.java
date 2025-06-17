package xiaozhi.modules.agent.service.impl;

import java.util.List;

import org.springframework.stereotype.Service;

import com.baomidou.mybatisplus.core.conditions.update.UpdateWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;

import lombok.RequiredArgsConstructor;
import xiaozhi.modules.agent.dao.AgentPluginMappingMapper;
import xiaozhi.modules.agent.entity.AgentPluginMapping;
import xiaozhi.modules.agent.service.AgentPluginMappingService;

/**
 * @description 针对表【ai_agent_plugin_mapping(Agent与插件的唯一映射表)】的数据库操作Service实现
 * @createDate 2025-05-25 22:33:17
 */
@Service
@RequiredArgsConstructor
public class AgentPluginMappingServiceImpl extends ServiceImpl<AgentPluginMappingMapper, AgentPluginMapping>
        implements AgentPluginMappingService {
    private final AgentPluginMappingMapper agentPluginMappingMapper;

    @Override
    public List<AgentPluginMapping> agentPluginParamsByAgentId(String agentId) {
        return agentPluginMappingMapper.selectPluginsByAgentId(agentId);
    }

    @Override
    public void deleteByAgentId(String agentId) {
        UpdateWrapper<AgentPluginMapping> updateWrapper = new UpdateWrapper<>();
        updateWrapper.eq("agent_id", agentId);
        agentPluginMappingMapper.delete(updateWrapper);
    }

}
