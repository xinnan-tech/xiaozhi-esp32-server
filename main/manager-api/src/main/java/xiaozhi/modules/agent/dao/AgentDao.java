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
     * 锁定智能体主记录，用于串行化同一智能体的配置写入
     *
     * @param agentId 智能体ID
     */
    AgentEntity selectByIdForUpdate(@Param("agentId") String agentId);

    /**
     * 精确写入快照覆盖的智能体字段，包括目标快照中的 null 值。
     * 不更新所属用户、创建信息等不属于快照的字段。
     *
     * @param agent 已应用目标快照的智能体
     * @return 受影响行数
     */
    int updateSnapshotFields(@Param("agent") AgentEntity agent);
}
