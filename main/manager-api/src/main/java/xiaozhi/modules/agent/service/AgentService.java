package xiaozhi.modules.agent.service;

import java.util.List;
import java.util.Map;

import xiaozhi.common.page.PageData;
import xiaozhi.common.service.BaseService;
import xiaozhi.modules.agent.dto.AgentDTO;
import xiaozhi.modules.agent.entity.AgentEntity;

/**
 * 智能体表处理service
 *
 * @author Goody
 * @version 1.0, 2025/4/30
 * @since 1.0.0
 */
public interface AgentService extends BaseService<AgentEntity> {
    /**
     * 获取管理员智能体列表
     *
     * @param params 查询参数
     * @return 分页数据
     */
    PageData<AgentEntity> adminAgentList(Map<String, Object> params);

    /**
     * 根据ID获取智能体
     *
     * @param id 智能体ID
     * @return 智能体实体
     */
    AgentEntity getAgentById(String id);

    /**
     * 插入智能体
     *
     * @param entity 智能体实体
     * @return 是否成功
     */
    boolean insert(AgentEntity entity);

    /**
     * 根据用户ID删除智能体
     *
     * @param userId 用户ID
     */
    void deleteAgentByUserId(Long userId);

    /**
     * 获取用户智能体列表
     *
     * @param userId 用户ID
     * @return 智能体列表
     */
    List<AgentDTO> getUserAgents(Long userId);

    /**
     * 根据智能体ID获取设备数量
     *
     * @param agentId 智能体ID
     * @return 设备数量
     */
    Integer getDeviceCountByAgentId(String agentId);

    /**
     * 根据设备MAC地址查询对应设备的默认智能体信息
     *
     * @param macAddress 设备MAC地址
     * @return 默认智能体信息，不存在时返回null
     */
    AgentEntity getDefaultAgentByMacAddress(String macAddress);

    /**
     * 检查用户是否有权限访问智能体
     *
     * @param agentId 智能体ID
     * @param userId  用户ID
     * @return 是否有权限
     */
    boolean checkAgentPermission(String agentId, Long userId);
}
