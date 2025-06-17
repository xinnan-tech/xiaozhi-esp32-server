package xiaozhi.modules.agent.dao;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import xiaozhi.modules.agent.entity.AgentPluginMapping;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;

import java.util.List;

/**
* @description 针对表【ai_agent_plugin_mapping(Agent与插件的唯一映射表)】的数据库操作Mapper
* @createDate 2025-05-25 22:33:17
* @Entity xiaozhi.modules.agent.entity.AgentPluginMapping
*/
@Mapper
public interface AgentPluginMappingMapper extends BaseMapper<AgentPluginMapping> {
    List<AgentPluginMapping> selectPluginsByAgentId(@Param("agentId") String agentId);
}




