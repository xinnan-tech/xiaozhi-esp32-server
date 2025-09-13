package xiaozhi.modules.agent.dao;

import java.util.List;
import java.util.Map;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import xiaozhi.common.dao.BaseDao;
import xiaozhi.modules.agent.entity.AgentEntity;
import xiaozhi.modules.agent.vo.AgentInfoVO;

@Mapper
public interface AgentDao extends BaseDao<AgentEntity> {
    /**
     * 获取智能体的设备数量
     * 
     * @param agentId 智能体ID
     * @return 设备数量
     */
    Integer getDeviceCountByAgentId(@Param("agentId") String agentId);

    /**
     * 根据设备MAC地址查询对应设备的默认智能体信息
     *
     * @param macAddress 设备MAC地址
     * @return 默认智能体信息
     */
    @Select(" SELECT a.* FROM ai_device d " +
            " LEFT JOIN ai_agent a ON d.agent_id = a.id " +
            " WHERE d.mac_address = #{macAddress} " +
            " ORDER BY d.id DESC LIMIT 1")
    AgentEntity getDefaultAgentByMacAddress(@Param("macAddress") String macAddress);

    /**
     * 获取所有智能体及其所有者信息（管理员专用）
     *
     * @return 所有智能体列表及用户信息
     */
    @Select("SELECT " +
            "a.id, a.agent_name, a.system_prompt, a.tts_model_id, " +
            "a.llm_model_id, a.vllm_model_id, a.mem_model_id, a.tts_voice_id, " +
            "a.created_at, a.updated_at, a.user_id, " +
            "u.username as owner_username, " +
            "GROUP_CONCAT(d.mac_address SEPARATOR ',') as device_mac_addresses " +
            "FROM ai_agent a " +
            "LEFT JOIN sys_user u ON a.user_id = u.id " +
            "LEFT JOIN ai_device d ON a.id = d.agent_id " +
            "GROUP BY a.id " +
            "ORDER BY a.created_at DESC")
    List<Map<String, Object>> getAllAgentsWithOwnerInfo();

    /**
     * 根据id查询agent信息，包括插件信息
     *
     * @param agentId 智能体ID
     */
    AgentInfoVO selectAgentInfoById(@Param("agentId") String agentId);
}
