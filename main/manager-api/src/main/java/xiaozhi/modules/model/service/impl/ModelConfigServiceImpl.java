package xiaozhi.modules.model.service.impl;

import java.io.Serializable;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.incrementer.DefaultIdentifierGenerator;
import com.baomidou.mybatisplus.core.metadata.IPage;
import cn.hutool.core.collection.CollectionUtil;
import cn.hutool.json.JSONObject;
import lombok.AllArgsConstructor;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.page.PageData;
import xiaozhi.common.redis.RedisKeys;
import xiaozhi.common.redis.RedisUtils;
import xiaozhi.common.service.impl.BaseServiceImpl;
import xiaozhi.common.utils.ConvertUtils;
import xiaozhi.common.utils.SensitiveDataUtils;
import xiaozhi.modules.agent.dao.AgentDao;
import xiaozhi.modules.agent.entity.AgentEntity;
import xiaozhi.modules.model.dao.ModelConfigDao;
import xiaozhi.modules.model.dto.LlmModelBasicInfoDTO;
import xiaozhi.modules.model.dto.ModelBasicInfoDTO;
import xiaozhi.modules.model.dto.ModelConfigBodyDTO;
import xiaozhi.modules.model.dto.ModelConfigDTO;
import xiaozhi.modules.model.dto.ModelProviderDTO;
import xiaozhi.modules.model.entity.ModelConfigEntity;
import xiaozhi.modules.model.service.ModelConfigService;
import xiaozhi.modules.model.service.ModelProviderService;
import lombok.extern.slf4j.Slf4j;
import xiaozhi.modules.model.support.ProviderPolicy;

@Service
@AllArgsConstructor
@Slf4j
public class ModelConfigServiceImpl extends BaseServiceImpl<ModelConfigDao, ModelConfigEntity>
        implements ModelConfigService {

    private final ModelConfigDao modelConfigDao;
    private final ModelProviderService modelProviderService;
    private final RedisUtils redisUtils;
    private final AgentDao agentDao;

    @Override
    public List<ModelBasicInfoDTO> getModelCodeList(String modelType, String modelName) {
        List<ModelConfigEntity> entities = modelConfigDao.selectList(
                new QueryWrapper<ModelConfigEntity>()
                        .eq("model_type", modelType)
                        .eq("is_enabled", 1)
                        .like(StringUtils.isNotBlank(modelName), "model_name", modelName)
                        .select("id", "model_name", "model_code", "config_json")
                        .orderByAsc("sort"));
        List<ModelConfigEntity> filtered = entities.stream()
                .filter(ProviderPolicy::isAllowedModelConfig)
                .collect(Collectors.toList());
        return ConvertUtils.sourceToTarget(filtered, ModelBasicInfoDTO.class);
    }

    @Override
    public List<LlmModelBasicInfoDTO> getLlmModelCodeList(String modelName) {
        List<ModelConfigEntity> entities = modelConfigDao.selectList(
                new QueryWrapper<ModelConfigEntity>()
                        .eq("model_type", "LLM")
                        .eq("is_enabled", 1)
                        .like(StringUtils.isNotBlank(modelName), "model_name", modelName)
                        .select("id", "model_name", "config_json"));

        return entities.stream()
                .filter(ProviderPolicy::isAllowedModelConfig)
                .map(item -> {
                    LlmModelBasicInfoDTO dto = new LlmModelBasicInfoDTO();
                    dto.setId(item.getId());
                    dto.setModelName(item.getModelName());
                    JSONObject configJson = item.getConfigJson();
                    String type = configJson != null ? configJson.getOrDefault("type", "").toString() : "";
                    dto.setType(type);
                    return dto;
                })
                .toList();
    }

    @Override
    public PageData<ModelConfigDTO> getPageList(String modelType, String modelName, String page, String limit) {
        long curPage = Long.parseLong(page);
        long pageSize = Long.parseLong(limit);

        QueryWrapper<ModelConfigEntity> wrapper = new QueryWrapper<ModelConfigEntity>()
                .eq("model_type", modelType)
                .like(StringUtils.isNotBlank(modelName), "model_name", modelName)
                .orderByDesc("is_enabled")
                .orderByAsc("sort");

        List<ModelConfigEntity> allRecords = modelConfigDao.selectList(wrapper);
        List<ModelConfigEntity> filteredRecords = allRecords.stream()
                .filter(ProviderPolicy::isAllowedModelConfig)
                .collect(Collectors.toList());

        int total = filteredRecords.size();
        int fromIndex = (int) Math.min((curPage - 1) * pageSize, total);
        int toIndex = (int) Math.min(fromIndex + pageSize, total);
        List<ModelConfigEntity> pageRecords = filteredRecords.subList(fromIndex, toIndex);

        for (ModelConfigEntity entity : pageRecords) {
            if (entity.getConfigJson() != null) {
                entity.setConfigJson(maskSensitiveFields(entity.getConfigJson()));
            }
        }

        List<ModelConfigDTO> dtoList = ConvertUtils.sourceToTarget(pageRecords, ModelConfigDTO.class);
        return new PageData<>(dtoList, total);
    }

    @Override
    public ModelConfigDTO edit(String modelType, String provideCode, String id, ModelConfigBodyDTO modelConfigBodyDTO) {
        // 1. Validate parameters.
        validateEditParameters(modelType, provideCode, id, modelConfigBodyDTO);

        // 2. Validate the model provider.
        validateModelProvider(modelType, provideCode);

        // 3. Load the original config without masking sensitive data.
        ModelConfigEntity originalEntity = getOriginalConfigFromDb(id);

        // 4. Validate LLM config constraints.
        validateLlmConfiguration(modelConfigBodyDTO);

        // 5. Prepare the updated entity and preserve sensitive fields correctly.
        ModelConfigEntity modelConfigEntity = prepareUpdateEntity(modelConfigBodyDTO, originalEntity, modelType, id);

        // 6. Persist the database update.
        modelConfigDao.updateById(modelConfigEntity);

        // 7. Clear cache entries.
        clearModelCache(id);

        // 8. Return the masked response DTO.
        return buildResponseDTO(modelConfigEntity);
    }

    @Override
    public ModelConfigDTO add(String modelType, String provideCode, ModelConfigBodyDTO modelConfigBodyDTO) {
        validateAddParameters(modelType, provideCode, modelConfigBodyDTO);

        validateModelProvider(modelType, provideCode);

        ModelConfigEntity modelConfigEntity = prepareAddEntity(modelConfigBodyDTO, modelType);

        modelConfigDao.insert(modelConfigEntity);

        return buildResponseDTO(modelConfigEntity);
    }

    @Override
    public void delete(String id) {
        if (StringUtils.isBlank(id)) {
            throw new RenException(ErrorCode.IDENTIFIER_NOT_NULL);
        }

        ModelConfigEntity modelConfig = modelConfigDao.selectById(id);
        if (modelConfig != null && modelConfig.getIsDefault() == 1) {
            throw new RenException(ErrorCode.DEFAULT_MODEL_DELETE_ERROR);
        }

        checkAgentReference(id);
        checkIntentConfigReference(id);

        modelConfigDao.deleteById(id);

        clearModelCache(id);
    }

    @Override
    public String getModelNameById(String id) {
        if (StringUtils.isBlank(id)) {
            return null;
        }

        String cacheKey = RedisKeys.getModelNameById(id);
        String cachedName = (String) redisUtils.get(cacheKey);
        if (StringUtils.isNotBlank(cachedName)) {
            return cachedName;
        }

        ModelConfigEntity entity = modelConfigDao.selectById(id);
        if (entity != null) {
            String modelName = entity.getModelName();
            if (StringUtils.isNotBlank(modelName)) {
                redisUtils.set(cacheKey, modelName);
            }
            return modelName;
        }

        return null;
    }

    @Override
    public ModelConfigEntity selectById(Serializable id) {
        ModelConfigEntity entity = super.selectById(id);
        if (entity != null && entity.getConfigJson() != null) {
            entity.setConfigJson(maskSensitiveFields(entity.getConfigJson()));
        }
        return entity;
    }

    @Override
    protected <D> PageData<D> getPageData(IPage<?> page, Class<D> target) {
        List<?> records = page.getRecords();
        if (records != null && !records.isEmpty()) {
            for (Object record : records) {
                if (record instanceof ModelConfigEntity) {
                    ModelConfigEntity entity = (ModelConfigEntity) record;
                    if (entity.getConfigJson() != null) {
                        entity.setConfigJson(maskSensitiveFields(entity.getConfigJson()));
                    }
                }
            }
        }
        return super.getPageData(page, target);
    }

    @Override
    public ModelConfigEntity getModelByIdFromCache(String id) {
        if (StringUtils.isBlank(id)) {
            return null;
        }
        String cacheKey = RedisKeys.getModelConfigById(id);
        ModelConfigEntity entity = (ModelConfigEntity) redisUtils.get(cacheKey);
        if (entity == null) {
            entity = modelConfigDao.selectById(id);
            if (entity != null) {
                redisUtils.set(cacheKey, entity);
            }
        }
        return entity;
    }

    /**
     * Validate edit parameters.
     */
    private void validateEditParameters(String modelType, String provideCode, String id,
            ModelConfigBodyDTO modelConfigBodyDTO) {
        if (StringUtils.isBlank(modelType) || StringUtils.isBlank(provideCode)) {
            throw new RenException(ErrorCode.MODEL_TYPE_PROVIDE_CODE_NOT_NULL);
        }
        if (StringUtils.isBlank(id)) {
            throw new RenException(ErrorCode.IDENTIFIER_NOT_NULL);
        }
        if (modelConfigBodyDTO == null) {
            throw new RenException(ErrorCode.PARAMS_GET_ERROR);
        }
    }

    /**
     * Validate add parameters.
     */
    private void validateAddParameters(String modelType, String provideCode, ModelConfigBodyDTO modelConfigBodyDTO) {
        if (StringUtils.isBlank(modelType) || StringUtils.isBlank(provideCode)) {
            throw new RenException(ErrorCode.MODEL_TYPE_PROVIDE_CODE_NOT_NULL);
        }
        if (modelConfigBodyDTO == null) {
            throw new RenException(ErrorCode.PARAMS_GET_ERROR);
        }
        if (StringUtils.isBlank(modelConfigBodyDTO.getId())) {
            // Follow the MP @TableId AutoUUID strategy:
            // com.baomidou.mybatisplus.core.incrementer.DefaultIdentifierGenerator(UUID.replace("-",""))
            // Assign a default model ID.
            modelConfigBodyDTO.setId(DefaultIdentifierGenerator.getInstance().nextUUID(ModelConfigEntity.class));
        }
    }

    /**
     * Set the default model.
     */
    @Override
    public void setDefaultModel(String modelType, int isDefault) {
        // Validate input.
        if (StringUtils.isBlank(modelType)) {
            throw new RenException(ErrorCode.MODEL_TYPE_PROVIDE_CODE_NOT_NULL);
        }

        ModelConfigEntity entity = new ModelConfigEntity();
        entity.setIsDefault(isDefault);
        modelConfigDao.update(entity, new QueryWrapper<ModelConfigEntity>()
                .eq("model_type", modelType));

        // Clear related caches.
        clearModelCacheByType(modelType);
    }

    /**
     * Validate the model provider.
     */
    private void validateModelProvider(String modelType, String provideCode) {
        List<ModelProviderDTO> providerList = modelProviderService.getList(modelType, provideCode);
        if (CollectionUtil.isEmpty(providerList)) {
            throw new RenException(ErrorCode.MODEL_PROVIDER_NOT_EXIST);
        }
    }

    /**
     * Load the original configuration from the database without masking sensitive fields.
     */
    private ModelConfigEntity getOriginalConfigFromDb(String id) {
        ModelConfigEntity originalEntity = modelConfigDao.selectById(id);
        if (originalEntity == null) {
            throw new RenException(ErrorCode.RESOURCE_NOT_FOUND);
        }
        return originalEntity;
    }

    /**
     * Validate the LLM configuration.
     */
    private void validateLlmConfiguration(ModelConfigBodyDTO modelConfigBodyDTO) {
        if (modelConfigBodyDTO.getConfigJson() != null && modelConfigBodyDTO.getConfigJson().containsKey("llm")) {
            String llm = modelConfigBodyDTO.getConfigJson().get("llm").toString();
            ModelConfigEntity modelConfigEntity = modelConfigDao.selectOne(new LambdaQueryWrapper<ModelConfigEntity>()
                    .eq(ModelConfigEntity::getId, llm));

            if (modelConfigEntity == null) {
                throw new RenException(ErrorCode.LLM_NOT_EXIST);
            }

            String modelType = modelConfigEntity.getModelType();
            if (modelType == null || !"LLM".equals(modelType.toUpperCase())) {
                throw new RenException(ErrorCode.LLM_NOT_EXIST);
            }

            // Validate the LLM type.
            JSONObject configJson = modelConfigEntity.getConfigJson();
            if (configJson != null && configJson.containsKey("type")) {
                String type = configJson.get("type").toString();
                if (!"openai".equals(type) && !"ollama".equals(type)) {
                    throw new RenException(ErrorCode.INVALID_LLM_TYPE);
                }
            }
        }
    }

    /**
     * Prepare an updated entity while preserving sensitive fields.
     */
    private ModelConfigEntity prepareUpdateEntity(ModelConfigBodyDTO modelConfigBodyDTO,
            ModelConfigEntity originalEntity,
            String modelType,
            String id) {
        // 1. Copy the original entity and keep all existing data, including sensitive values.
        ModelConfigEntity modelConfigEntity = ConvertUtils.sourceToTarget(originalEntity, ModelConfigEntity.class);
        modelConfigEntity.setId(id);
        modelConfigEntity.setModelType(modelType);

        // 2. Update only non-sensitive fields directly.
        modelConfigEntity.setModelName(modelConfigBodyDTO.getModelName());
        modelConfigEntity.setSort(modelConfigBodyDTO.getSort());
        modelConfigEntity.setIsEnabled(modelConfigBodyDTO.getIsEnabled());
        modelConfigEntity.setRemark(modelConfigBodyDTO.getRemark());
        // 3. Update config JSON, changing non-sensitive fields and only explicitly modified sensitive fields.
        if (modelConfigBodyDTO.getConfigJson() != null && originalEntity.getConfigJson() != null) {
            JSONObject originalJson = originalEntity.getConfigJson();
            JSONObject updatedJson = new JSONObject(originalJson); // Start from the original JSON.

            // Walk the incoming JSON and only update non-sensitive fields or truly changed sensitive fields.
            for (String key : modelConfigBodyDTO.getConfigJson().keySet()) {
                Object value = modelConfigBodyDTO.getConfigJson().get(key);

                // Sensitive fields must be checked because the UI may send masked values.
                if (SensitiveDataUtils.isSensitiveField(key)) {

                    if (value instanceof String && !SensitiveDataUtils.isMaskedValue((String) value)) {
                        updatedJson.set(key, value);
                    }
                } else if (value instanceof JSONObject) {
                    // Merge nested JSON recursively.
                    mergeJson(updatedJson, key, (JSONObject) value);
                } else {
                    // Update non-sensitive fields directly.
                    updatedJson.put(key, value);
                }
            }

            // 删除在新JSON中不存在的非敏感字段
            for (String oldKey : originalJson.keySet().toArray(new String[0])) {
                if (!modelConfigBodyDTO.getConfigJson().containsKey(oldKey)
                        && !SensitiveDataUtils.isSensitiveField(oldKey)) {
                    updatedJson.remove(oldKey);
                }
            }

            modelConfigEntity.setConfigJson(updatedJson);
        }

        return modelConfigEntity;
    }

    // Helper: detect whether a value is masked.
    private boolean isMaskedValue(String value) {
        if (value == null)
            return false;
        // Simple check for the masking pattern (***).
        return value.contains("***");
    }

    // Helper: recursively merge JSON while preserving original sensitive fields.
    private void mergeJson(JSONObject original, String key, JSONObject updated) {
        if (original == null || updated == null) {
            log.warn("mergeJson: original or updated is null");
            return;
        }

        // Create a new JSON object when the key is missing in the original payload.
        if (!original.containsKey(key)) {
            original.set(key, new JSONObject());
        }

        // 获取 original 中的子对象
        Object originalValue = original.get(key);
        JSONObject originalChild;

        // 检查 originalValue 是否是 JSONObject 类型
        if (originalValue instanceof JSONObject) {
            originalChild = (JSONObject) originalValue;
        } else {
            // 如果不是 JSONObject 类型，记录警告并创建新的 JSON 对象
            log.warn("mergeJson: key '{}' 的值不是 JSONObject 类型 (实际类型：{})，将创建新对象",
                    key, originalValue != null ? originalValue.getClass().getSimpleName() : "null");
            originalChild = new JSONObject();
            original.set(key, originalChild);
        }

        for (String childKey : updated.keySet()) {
            Object childValue = updated.get(childKey);
            if (childValue instanceof JSONObject) {
                mergeJson(originalChild, childKey, (JSONObject) childValue);
            } else {
                if (!SensitiveDataUtils.isSensitiveField(childKey) ||
                        (childValue instanceof String && !isMaskedValue((String) childValue))) {
                    originalChild.set(childKey, childValue);
                }
            }
        }

        // 删除在新 JSON 中不存在的非敏感子字段
        for (String oldChildKey : originalChild.keySet().toArray(new String[0])) {
            if (!updated.containsKey(oldChildKey) && !SensitiveDataUtils.isSensitiveField(oldChildKey)) {
                originalChild.remove(oldChildKey);
            }
        }
    }

    /**
     * Prepare a new entity.
     */
    private ModelConfigEntity prepareAddEntity(ModelConfigBodyDTO modelConfigBodyDTO, String modelType) {
        ModelConfigEntity modelConfigEntity = ConvertUtils.sourceToTarget(modelConfigBodyDTO, ModelConfigEntity.class);
        modelConfigEntity.setModelType(modelType);
        modelConfigEntity.setIsDefault(0);
        return modelConfigEntity;
    }

    /**
     * Build the response DTO and mask sensitive fields.
     */
    private ModelConfigDTO buildResponseDTO(ModelConfigEntity entity) {
        ModelConfigDTO dto = ConvertUtils.sourceToTarget(entity, ModelConfigDTO.class);
        if (dto.getConfigJson() != null) {
            dto.setConfigJson(maskSensitiveFields(dto.getConfigJson()));
        }
        return dto;
    }

    /**
     * Mask sensitive fields.
     */
    private JSONObject maskSensitiveFields(JSONObject configJson) {
        return SensitiveDataUtils.maskSensitiveFields(configJson);
    }

    /**
     * Clear the cache for a model.
     */
    private void clearModelCache(String id) {
        redisUtils.delete(RedisKeys.getModelConfigById(id));
        redisUtils.delete(RedisKeys.getModelNameById(id));
    }

    /**
     * Clear caches for a model type.
     */
    private void clearModelCacheByType(String modelType) {
        List<ModelConfigEntity> entities = modelConfigDao.selectList(
                new QueryWrapper<ModelConfigEntity>().eq("model_type", modelType));
        for (ModelConfigEntity entity : entities) {
            clearModelCache(entity.getId());
        }
    }

    /**
     * Check whether any agent configuration references the model.
     */
    private void checkAgentReference(String modelId) {
        List<AgentEntity> agents = agentDao.selectList(
                new QueryWrapper<AgentEntity>()
                        .eq("vad_model_id", modelId)
                        .or()
                        .eq("asr_model_id", modelId)
                        .or()
                        .eq("llm_model_id", modelId)
                        .or()
                        .eq("tts_model_id", modelId)
                        .or()
                        .eq("mem_model_id", modelId)
                        .or()
                        .eq("vllm_model_id", modelId)
                        .or()
                        .eq("intent_model_id", modelId));
        if (!agents.isEmpty()) {
            String agentNames = agents.stream()
                    .map(AgentEntity::getAgentName)
                    .collect(Collectors.joining("、"));
            throw new RenException(ErrorCode.MODEL_REFERENCED_BY_AGENT, agentNames);
        }
    }

    /**
     * Check whether any intent configuration references the model.
     */
    private void checkIntentConfigReference(String modelId) {
        ModelConfigEntity modelConfig = modelConfigDao.selectById(modelId);
        if (modelConfig != null
                && "LLM".equals(modelConfig.getModelType() == null ? null : modelConfig.getModelType().toUpperCase())) {
            List<ModelConfigEntity> intentConfigs = modelConfigDao.selectList(
                    new QueryWrapper<ModelConfigEntity>()
                            .eq("model_type", "Intent")
                            .like("config_json", modelId));
            if (!intentConfigs.isEmpty()) {
                throw new RenException(ErrorCode.LLM_REFERENCED_BY_INTENT);
            }
        }
    }

    /**
     * Get the list of TTS platforms that match the current criteria.
     */
    @Override
    public List<Map<String, Object>> getTtsPlatformList() {
        return modelConfigDao.getTtsPlatformList();
    }

    /**
     * Get all enabled model configurations for the given model type.
     */
    @Override
    public List<ModelConfigEntity> getEnabledModelsByType(String modelType) {
        if (StringUtils.isBlank(modelType)) {
            return null;
        }

        List<ModelConfigEntity> entities = modelConfigDao.selectList(
                new QueryWrapper<ModelConfigEntity>()
                        .eq("model_type", modelType)
                        .eq("is_enabled", 1)
                        .orderByAsc("sort"));

        return entities.stream()
                .filter(ProviderPolicy::isAllowedModelConfig)
                .collect(Collectors.toList());
    }
}
