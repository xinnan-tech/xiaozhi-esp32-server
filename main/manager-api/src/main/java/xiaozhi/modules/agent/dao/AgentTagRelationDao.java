package xiaozhi.modules.agent.dao;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import xiaozhi.common.dao.BaseDao;
import xiaozhi.modules.agent.entity.AgentTagRelationEntity;

import java.util.List;

@Mapper
public interface AgentTagRelationDao extends BaseDao<AgentTagRelationEntity> {

    int deleteByAgentId(@Param("agentId") String agentId);

    int insertRelation(AgentTagRelationEntity relation);

    int batchInsertRelation(@Param("list") List<AgentTagRelationEntity> relations);
}
