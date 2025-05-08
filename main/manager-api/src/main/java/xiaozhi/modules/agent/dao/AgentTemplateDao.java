package xiaozhi.modules.agent.dao;

import org.apache.ibatis.annotations.Mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;

import xiaozhi.modules.agent.entity.AgentTemplateEntity;

/**
 * @author chenerlei
 * @description 针对表【ai_agent_template(智能体配置模板表)】的数据库操作Mapper
 * @createDate 2025-03-22 11:48:18
 */
@Mapper
public interface AgentTemplateDao extends BaseMapper<AgentTemplateEntity> {

}
