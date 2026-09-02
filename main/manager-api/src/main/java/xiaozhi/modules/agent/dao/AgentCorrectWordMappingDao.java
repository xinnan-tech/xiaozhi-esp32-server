package xiaozhi.modules.agent.dao;

import java.util.List;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import xiaozhi.common.dao.BaseDao;
import xiaozhi.modules.agent.entity.AgentCorrectWordMappingEntity;

@Mapper
public interface AgentCorrectWordMappingDao extends BaseDao<AgentCorrectWordMappingEntity> {

    int deleteByAgentId(@Param("agentId") String agentId);

    int deleteByFileId(@Param("fileId") String fileId);

    int batchInsertMapping(@Param("list") List<AgentCorrectWordMappingEntity> mappings);

    List<AgentCorrectWordMappingEntity> selectByAgentId(@Param("agentId") String agentId);
}
