package xiaozhi.modules.agent.service.impl;

import org.springframework.stereotype.Service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.UpdateWrapper;
import com.baomidou.mybatisplus.spring.repository.CrudRepository;

import xiaozhi.modules.agent.dao.AgentTemplateDao;
import xiaozhi.modules.agent.entity.AgentTemplateEntity;
import xiaozhi.modules.agent.service.AgentTemplateService;

import java.util.List;
import java.util.Objects;
import java.util.stream.Collectors;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;

/**
 * @author chenerlei
 * @description Database operation Service implementation for table [ai_agent_template(agent configuration template table)]
 * @createDate 2025-03-22 11:48:18
 */
@Service
public class AgentTemplateServiceImpl extends CrudRepository<AgentTemplateDao, AgentTemplateEntity>
        implements AgentTemplateService {

    /**
     * Get default template
     * 
     * @return Default template entity
     */
    public AgentTemplateEntity getDefaultTemplate() {
        LambdaQueryWrapper<AgentTemplateEntity> wrapper = new LambdaQueryWrapper<>();
        wrapper.orderByAsc(AgentTemplateEntity::getSort)
                .last("LIMIT 1");
        return this.getOne(wrapper);
    }

    /**
     * Update model ID in default template
     * 
     * @param modelType Model type
     * @param modelId   Model ID
     */
    @Override
    public void updateDefaultTemplateModelId(String modelType, String modelId) {
        modelType = modelType.toUpperCase();
        // Skip updates for RAG models.
        if (modelType.equals("RAG")) {
            return;
        }

        UpdateWrapper<AgentTemplateEntity> wrapper = new UpdateWrapper<>();
        switch (modelType) {
            case "ASR":
                wrapper.set("asr_model_id", modelId);
                break;
            case "VAD":
                wrapper.set("vad_model_id", modelId);
                break;
            case "LLM":
                wrapper.set("llm_model_id", modelId);
                break;
            case "TTS":
                wrapper.set("tts_model_id", modelId);
                wrapper.set("tts_voice_id", null);
                break;
            case "VLLM":
                wrapper.set("vllm_model_id", modelId);
                break;
            case "MEMORY":
                wrapper.set("mem_model_id", modelId);
                break;
            case "INTENT":
                wrapper.set("intent_model_id", modelId);
                break;
        }
        wrapper.ge("sort", 0);
        update(wrapper);
    }

    @Override
    public void reorderTemplatesAfterDelete(Integer deletedSort) {
        if (deletedSort == null) {
            return;
        }
        
        // Query all records with sort value greater than the deleted template
        UpdateWrapper<AgentTemplateEntity> updateWrapper = new UpdateWrapper<>();
        updateWrapper.gt("sort", deletedSort)
                    .setSql("sort = sort - 1");
        
        // Execute batch update to decrease sort value by 1 for these records
        this.update(updateWrapper);
    }

    @Override
    public Integer getNextAvailableSort() {
        // Query all existing sort values and sort them in ascending order
        List<Integer> sortValues = baseMapper.selectList(new QueryWrapper<AgentTemplateEntity>())
                .stream()
                .map(AgentTemplateEntity::getSort)
                .filter(Objects::nonNull)
                .sorted()
                .collect(Collectors.toList());
        
        // If no sort values exist, return 1
        if (sortValues.isEmpty()) {
            return 1;
        }
        
        // Find the smallest unused sequence number
        int expectedSort = 1;
        for (Integer sort : sortValues) {
            if (sort > expectedSort) {
                // Found a gap in sequence numbers
                return expectedSort;
            }
            expectedSort = sort + 1;
        }
        
        // If no gaps found, return max sequence number + 1
        return expectedSort;
    }
}
