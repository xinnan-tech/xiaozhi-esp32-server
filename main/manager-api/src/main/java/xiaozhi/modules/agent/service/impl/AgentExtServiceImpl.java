package xiaozhi.modules.agent.service.impl;

import org.springframework.stereotype.Service;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;

import xiaozhi.modules.agent.dao.AgentExtDao;
import xiaozhi.modules.agent.entity.AgentExtEntity;
import xiaozhi.modules.agent.service.AgentExtService;

@Service
public class AgentExtServiceImpl
        extends ServiceImpl<AgentExtDao, AgentExtEntity>
        implements AgentExtService {

    @Override
    public AgentExtEntity getByAgentId(String agentId) {
        if (agentId == null || agentId.isBlank()) {
            return null;
        }
        // agentId 即主键(@TableId IdType.INPUT),直接 getById
        return this.getById(agentId);
    }

    @Override
    public void saveOrUpdate(String agentId, String extJson) {
        AgentExtEntity e = getByAgentId(agentId);
        if (e == null) {
            e = new AgentExtEntity();
            e.setAgentId(agentId);
        }
        e.setExtJson(extJson);
        this.saveOrUpdate(e);
    }
}
