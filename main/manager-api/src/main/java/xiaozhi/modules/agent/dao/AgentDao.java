package xiaozhi.modules.agent.dao;

import org.apache.ibatis.annotations.Mapper;

import xiaozhi.common.dao.BaseDao;
import xiaozhi.modules.agent.entity.AgentEntity;

@Mapper
public interface AgentDao extends BaseDao<AgentEntity> {

}