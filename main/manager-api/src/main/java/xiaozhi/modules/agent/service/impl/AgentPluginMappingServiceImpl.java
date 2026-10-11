package xiaozhi.modules.agent.service.impl;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Service;

import com.baomidou.mybatisplus.core.conditions.update.UpdateWrapper;
import com.baomidou.mybatisplus.spring.repository.CrudRepository;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import xiaozhi.common.utils.JsonUtils;
import xiaozhi.modules.agent.dao.AgentPluginMappingMapper;
import xiaozhi.modules.agent.entity.AgentPluginMapping;
import xiaozhi.modules.agent.service.AgentPluginMappingService;
import xiaozhi.modules.knowledge.entity.KnowledgeBaseEntity;
import xiaozhi.modules.knowledge.service.KnowledgeBaseService;
import xiaozhi.modules.model.entity.ModelConfigEntity;
import xiaozhi.modules.model.service.ModelConfigService;

/**
 * @description Database operation Service implementation for table [ai_agent_plugin_mapping(unique mapping table between Agent and plugins)]
 * @createDate 2025-05-25 22:33:17
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class AgentPluginMappingServiceImpl extends CrudRepository<AgentPluginMappingMapper, AgentPluginMapping>
        implements AgentPluginMappingService {
    private final AgentPluginMappingMapper agentPluginMappingMapper;
    private final KnowledgeBaseService knowledgeBaseService;
    private final ModelConfigService modelConfigService;

    @Override
    public List<AgentPluginMapping> agentPluginParamsByAgentId(String agentId) {
        List<AgentPluginMapping> list = agentPluginMappingMapper.selectPluginsByAgentId(agentId);
        Map<String, List<KnowledgeBaseEntity>> knowledgeBaseMap = new HashMap<>();
        Map<String, ModelConfigEntity> modelConfigMap = new HashMap<>();
        for (int i = list.size() - 1; i >= 0; i--) {
            AgentPluginMapping mapping = list.get(i);
            if (StringUtils.isBlank(mapping.getProviderCode())) {
                // Load knowledge-base plugin parameters.
                KnowledgeBaseEntity knowledgeBaseEntity = knowledgeBaseService.selectById(mapping.getPluginId());
                if (knowledgeBaseEntity == null) {
                    list.remove(i);
                    continue;
                }
                ModelConfigEntity modelConfigEntity = modelConfigService
                        .getModelByIdFromCache(knowledgeBaseEntity.getRagModelId());
                if (modelConfigEntity == null) {
                    list.remove(i);
                    continue;
                }
                List<KnowledgeBaseEntity> knowledgeBaseList = knowledgeBaseMap.get(modelConfigEntity.getModelCode());
                if (knowledgeBaseList == null) {
                    knowledgeBaseList = new ArrayList<>();
                }
                modelConfigMap.put(modelConfigEntity.getModelCode(), modelConfigEntity);
                knowledgeBaseList.add(knowledgeBaseEntity);
                knowledgeBaseMap.put(modelConfigEntity.getModelCode(), knowledgeBaseList);
                list.remove(i);
            }
        }
        if (knowledgeBaseMap.size() > 0) {
            for (String pluginCode : knowledgeBaseMap.keySet()) {
                List<KnowledgeBaseEntity> knowledgeBaseList = knowledgeBaseMap.get(pluginCode);
                if (knowledgeBaseList == null || knowledgeBaseList.isEmpty()) {
                    continue;
                }

                AgentPluginMapping agentPluginMapping = new AgentPluginMapping();
                agentPluginMapping.setAgentId(agentId);
                agentPluginMapping.setPluginId(pluginCode);
                agentPluginMapping.setProviderCode("search_from_" + pluginCode);
                agentPluginMapping.setId(Long.valueOf(list.size() + 1));

                Map<String, Object> paramInfo = new HashMap<>(4);
                ModelConfigEntity modelConfigEntity = modelConfigMap.get(pluginCode);
                paramInfo.put("base_url", modelConfigEntity.getConfigJson().getStr("base_url"));
                paramInfo.put("api_key", modelConfigEntity.getConfigJson().getStr("api_key"));
                paramInfo.put("dataset_ids",
                        knowledgeBaseList.stream().map(KnowledgeBaseEntity::getDatasetId).toList());

                String description = "Use this method when the user asks about content related to ["
                        + String.join(",", knowledgeBaseList.stream().map(KnowledgeBaseEntity::getName).toList())
                        + "] and use it to query: " + String.join(",",
                                knowledgeBaseList.stream().map(KnowledgeBaseEntity::getDescription).toList());
                paramInfo.put("description", description);
                agentPluginMapping.setParamInfo(JsonUtils.toJsonString(paramInfo));
                list.add(agentPluginMapping);
            }
        }
        return list;
    }

    @Override
    public void deleteByAgentId(String agentId) {
        UpdateWrapper<AgentPluginMapping> updateWrapper = new UpdateWrapper<>();
        updateWrapper.eq("agent_id", agentId);
        agentPluginMappingMapper.delete(updateWrapper);
    }

    @Override
    public void deleteByPluginId(String pluginId) {
        UpdateWrapper<AgentPluginMapping> updateWrapper = new UpdateWrapper<>();
        updateWrapper.eq("plugin_id", pluginId);
        agentPluginMappingMapper.delete(updateWrapper);
    }

}
