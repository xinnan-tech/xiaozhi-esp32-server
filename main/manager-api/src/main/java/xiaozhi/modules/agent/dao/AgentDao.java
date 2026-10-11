package xiaozhi.modules.agent.dao;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import org.apache.ibatis.annotations.Select;
import xiaozhi.common.dao.BaseDao;
import xiaozhi.modules.agent.entity.AgentEntity;
import xiaozhi.modules.agent.vo.AgentInfoVO;

@Mapper
public interface AgentDao extends BaseDao<AgentEntity> {
    /**
     * Get device count for agent
     * 
     * @param agentId Agent ID
     * @return Device count
     */
    Integer getDeviceCountByAgentId(@Param("agentId") String agentId);

    /**
     * Query default agent information for device by device MAC address
     *
     * @param macAddress Device MAC address
     * @return Default agent information
     */
    @Select(" SELECT a.* FROM ai_device d " +
            " LEFT JOIN ai_agent a ON d.agent_id = a.id " +
            " WHERE d.mac_address = #{macAddress} " +
            " ORDER BY d.id DESC LIMIT 1")
    AgentEntity getDefaultAgentByMacAddress(@Param("macAddress") String macAddress);

    /**
     * Query agent information by ID, including plugin information
     *
     * @param agentId Agent ID
     */
    AgentInfoVO selectAgentInfoById(@Param("agentId") String agentId);

    /**
     * Lock Agent main record to serialize config writes for the same Agent
     *
     * @param agentId Agent ID
     */
    AgentEntity selectByIdForUpdate(@Param("agentId") String agentId);

    /**
     * Precisely overwrite Agent fields in the snapshot, including null values from the target snapshot.
     * Do not update fields not included in the snapshot, such as owner user and creation info
     *
     * @param agent Agent with target snapshot applied
     * @return Number of affected rows
     */
    int updateSnapshotFields(@Param("agent") AgentEntity agent);
}
