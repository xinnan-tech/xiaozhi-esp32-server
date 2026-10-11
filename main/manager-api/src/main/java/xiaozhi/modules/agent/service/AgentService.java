package xiaozhi.modules.agent.service;

import java.util.List;
import java.util.Map;

import xiaozhi.common.page.PageData;
import xiaozhi.common.service.BaseService;
import xiaozhi.modules.agent.dto.AgentCreateDTO;
import xiaozhi.modules.agent.dto.AgentDTO;
import xiaozhi.modules.agent.dto.AgentMemoryDTO;
import xiaozhi.modules.agent.dto.AgentUpdateDTO;
import xiaozhi.modules.agent.entity.AgentEntity;
import xiaozhi.modules.agent.vo.AgentInfoVO;

/**
 * Agent service interface.
 *
 * @author Goody
 * @version 1.0, 2025/4/30
 * @since 1.0.0
 */
public interface AgentService extends BaseService<AgentEntity> {
    /**
     * Get the admin-facing agent list.
     *
     * @param params query parameters
     * @return paginated data
     */
    PageData<AgentEntity> adminAgentList(Map<String, Object> params);

    /**
     * Get an agent by ID.
     *
     * @param id agent ID
     * @return agent details
     */
    AgentInfoVO getAgentById(String id);

    /**
     * Insert an agent.
     *
     * @param entity agent entity
     * @return whether the operation succeeded
     */
    boolean insert(AgentEntity entity);

    /**
     * Delete agents by user ID.
     *
     * @param userId user ID
     */
    void deleteAgentByUserId(Long userId);

    /**
     * Get a user's agents.
     *
     * @param userId user ID
     * @param keyword search keyword
     * @param searchType search type: `name` for agent name, `mac` for MAC address
     * @return agent list
     */
    List<AgentDTO> getUserAgents(Long userId, String keyword, String searchType);

    /**
     * Get the number of devices linked to an agent.
     *
     * @param agentId agent ID
     * @return device count
     */
    Integer getDeviceCountByAgentId(String agentId);

    /**
     * Get the default agent linked to a device MAC address.
     *
     * @param macAddress device MAC address
     * @return default agent info, or {@code null} if none exists
     */
    AgentEntity getDefaultAgentByMacAddress(String macAddress);

    /**
     * Check whether a user can access an agent.
     *
     * @param agentId agent ID
     * @param userId  user ID
     * @return whether access is allowed
     */
    boolean checkAgentPermission(String agentId, Long userId);

    /**
     * Update an agent.
     *
     * @param agentId agent ID
     * @param dto     updated agent data
     */
    void updateAgentById(String agentId, AgentUpdateDTO dto);

    /**
     * Create an agent.
     *
     * @param dto agent data needed for creation
     * @return created agent ID
     */
    String createAgent(AgentCreateDTO dto);


}
