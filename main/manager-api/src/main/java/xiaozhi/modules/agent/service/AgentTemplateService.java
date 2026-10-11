package xiaozhi.modules.agent.service;

import com.baomidou.mybatisplus.extension.repository.IRepository;

import xiaozhi.modules.agent.entity.AgentTemplateEntity;

/**
 * @author chenerlei
 * @description Database operation Service for table [ai_agent_template(agent configuration template table)]
 * @createDate 2025-03-22 11:48:18
 */
public interface AgentTemplateService extends IRepository<AgentTemplateEntity> {

    /**
     * Get default template
     * 
     * @return Default template entity
     */
    AgentTemplateEntity getDefaultTemplate();

    /**
     * Update model ID in default template
     * 
     * @param modelType Model type
     * @param modelId   Model ID
     */
    void updateDefaultTemplateModelId(String modelType, String modelId);

    /**
     * Reorder remaining templates after deleting a template
     * 
     * @param deletedSort Sort value of the deleted template
     */
    void reorderTemplatesAfterDelete(Integer deletedSort);

    /**
     * Get next available sort number (find smallest unused number)
     * 
     * @return Next available sort number
     */
    Integer getNextAvailableSort();
}
