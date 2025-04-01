package xiaozhi.modules.agent.service;

import java.util.List;
import java.util.Map;

import xiaozhi.common.page.PageData;
import xiaozhi.common.service.BaseService;
import xiaozhi.modules.agent.entity.AgentEntity;

public interface AgentService extends BaseService<AgentEntity> {
    /**
     * 根据用户ID获取智能体列表
     */
    List<AgentEntity> getUserAgents(Long userId);

    /**
     * 管理员获取所有智能体列表（分页）
     */
    PageData<AgentEntity> adminAgentList(Map<String, Object> params);

    /**
     * 获取智能体详情
     */
    AgentEntity getAgentById(String id);
}