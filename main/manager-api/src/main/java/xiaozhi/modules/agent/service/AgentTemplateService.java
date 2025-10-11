package xiaozhi.modules.agent.service;

import com.baomidou.mybatisplus.extension.service.IService;

import xiaozhi.modules.agent.entity.AgentTemplateEntity;

/**
 * @author chenerlei
 * @description 针对表【ai_agent_template(智能体配置模板表)】的数据库操作Service
 * @createDate 2025-03-22 11:48:18
 */
public interface AgentTemplateService extends IService<AgentTemplateEntity> {

    /**
     * 获取默认模板
     * 
     * @return 默认模板实体
     */
    AgentTemplateEntity getDefaultTemplate();

    /**
     * 更新默认模板中的模型ID
     * 
     * @param modelType 模型类型
     * @param modelId   模型ID
     */
    void updateDefaultTemplateModelId(String modelType, String modelId);

    /**
     * 删除模板后重新排序剩余模板
     * 
     * @param deletedSort 被删除模板的排序值
     */
    void reorderTemplatesAfterDelete(Integer deletedSort);

    /**
     * 获取下一个可用的排序序号（寻找最小的未使用序号）
     * 
     * @return 下一个可用的排序序号
     */
    Integer getNextAvailableSort();
}
