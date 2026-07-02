package xiaozhi.modules.agent.service;

import xiaozhi.modules.agent.entity.AgentExtEntity;

public interface AgentExtService {

    /** 取一个 agent 的扩展字段;无则 null。 */
    AgentExtEntity getByAgentId(String agentId);

    /** 整体覆盖一个 agent 的扩展字段(JSON 字符串)。 */
    void saveOrUpdate(String agentId, String extJson);
}
