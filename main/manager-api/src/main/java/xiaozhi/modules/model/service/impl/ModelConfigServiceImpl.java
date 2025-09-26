package xiaozhi.modules.model.service.impl;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.core.metadata.OrderItem; 
import com.baomidou.mybatisplus.extension.plugins.pagination.Page; 

import cn.hutool.core.collection.CollectionUtil;
import cn.hutool.json.JSONObject;
import lombok.AllArgsConstructor;
import xiaozhi.common.constant.Constant;
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

import java.io.Serializable;

@Service
@AllArgsConstructor
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
                        .like(StringUtils.isNotBlank(modelName), "model_name", "%" + modelName + "%")
                        .select("id", "model_name"));
        return ConvertUtils.sourceToTarget(entities, ModelBasicInfoDTO.class);
    }

    @Override
    public List<LlmModelBasicInfoDTO> getLlmModelCodeList(String modelName) {
        List<ModelConfigEntity> entities = modelConfigDao.selectList(
                new QueryWrapper<ModelConfigEntity>()
                        .eq("model_type", "llm")
                        .eq("is_enabled", 1)
                        .like(StringUtils.isNotBlank(modelName), "model_name", "%" + modelName + "%")
                        .select("id", "model_name", "config_json"));
        // 处理获取到的内容
        return entities.stream().map(item -> {
            LlmModelBasicInfoDTO dto = new LlmModelBasicInfoDTO();
            dto.setId(item.getId());
            dto.setModelName(item.getModelName());
            String type = item.getConfigJson().get("type").toString();
            dto.setType(type);
            return dto;
        }).toList();
    }

    @Override
    public PageData<ModelConfigDTO> getPageList(String modelType, String modelName, String page, String limit) {
        Map<String, Object> params = new HashMap<String, Object>();
        params.put(Constant.PAGE, page);
        params.put(Constant.LIMIT, limit);
        
        // 不再使用默认的getPage方法，而是直接创建Page对象并自定义排序
        long curPage = Long.parseLong(page);
        long pageSize = Long.parseLong(limit);
        Page<ModelConfigEntity> pageInfo = new Page<>(curPage, pageSize);
        
        // 添加排序规则：先按is_enabled降序，再按sort升序
        pageInfo.addOrder(OrderItem.desc("is_enabled"));
        pageInfo.addOrder(OrderItem.asc("sort"));
        
        // 执行分页查询
        IPage<ModelConfigEntity> modelConfigEntityIPage = modelConfigDao.selectPage(
                pageInfo,
                new QueryWrapper<ModelConfigEntity>()
                        .eq("model_type", modelType)
                        .like(StringUtils.isNotBlank(modelName), "model_name", "%" + modelName + "%"));
        
        return getPageData(modelConfigEntityIPage, ModelConfigDTO.class);
    }

    @Override
    public ModelConfigDTO edit(String modelType, String provideCode, String id, ModelConfigBodyDTO modelConfigBodyDTO) {
        // 先验证有没有供应器
        if (StringUtils.isBlank(modelType) || StringUtils.isBlank(provideCode)) {
            throw new RenException("modelType和provideCode不能为空");
        }
        List<ModelProviderDTO> providerList = modelProviderService.getList(modelType, provideCode);
        if (CollectionUtil.isEmpty(providerList)) {
            throw new RenException(ErrorCode.MODEL_PROVIDER_NOT_EXIST);
        }
        
        // 获取原始配置
        ModelConfigEntity originalEntity = modelConfigDao.selectById(id);
        if (originalEntity == null) {
            throw new RenException(ErrorCode.RESOURCE_NOT_FOUND);
        }
        
        // 验证LLM配置
        if (modelConfigBodyDTO.getConfigJson().containsKey("llm")) {
            String llm = modelConfigBodyDTO.getConfigJson().get("llm").toString();
            ModelConfigEntity modelConfigEntity = modelConfigDao.selectOne(new LambdaQueryWrapper<ModelConfigEntity>()
                    .eq(ModelConfigEntity::getId, llm));
            String selectModelType = (modelConfigEntity == null || modelConfigEntity.getModelType() == null) ? null
                    : modelConfigEntity.getModelType().toUpperCase();
            if (modelConfigEntity == null || !"LLM".equals(selectModelType)) {
                throw new RenException(ErrorCode.LLM_NOT_EXIST);
            }
            String type = modelConfigEntity.getConfigJson().get("type").toString();
            // 如果查询大语言模型是openai或者ollama，意图识别选参数都可以
            if (!"openai".equals(type) && !"ollama".equals(type)) {
                throw new RenException(ErrorCode.INVALID_LLM_TYPE);
            }
        }

        // 再更新供应器提供的模型
        ModelConfigEntity modelConfigEntity = ConvertUtils.sourceToTarget(modelConfigBodyDTO, ModelConfigEntity.class);
        modelConfigEntity.setId(id);
        modelConfigEntity.setModelType(modelType);
    
        // 检查敏感字段是否有变化
        if (originalEntity.getConfigJson() != null && modelConfigBodyDTO.getConfigJson() != null) {
            boolean sensitiveEqual = SensitiveDataUtils.isSensitiveDataEqual(
                    originalEntity.getConfigJson(), 
                    modelConfigBodyDTO.getConfigJson()
            );
            
            if (sensitiveEqual) {
                // 敏感数据没有变化，使用原始的configJson值
                modelConfigEntity.setConfigJson(originalEntity.getConfigJson());
            }
        }
        
        modelConfigDao.updateById(modelConfigEntity);
        
        // 清除缓存
        redisUtils.delete(RedisKeys.getModelConfigById(modelConfigEntity.getId()));
        
        // 返回数据前处理敏感字段
        ModelConfigDTO dto = ConvertUtils.sourceToTarget(modelConfigEntity, ModelConfigDTO.class);
        if (dto.getConfigJson() != null) {
            dto.setConfigJson(SensitiveDataUtils.maskSensitiveFields(dto.getConfigJson()));
        }
        
        return dto;
    }

    @Override
    public ModelConfigDTO add(String modelType, String provideCode, ModelConfigBodyDTO modelConfigBodyDTO) {
        // 先验证有没有供应器
        if (StringUtils.isBlank(modelType) || StringUtils.isBlank(provideCode)) {
            throw new RenException(ErrorCode.MODEL_TYPE_PROVIDE_CODE_NOT_NULL);
        }
        List<ModelProviderDTO> providerList = modelProviderService.getList(modelType, provideCode);
        if (CollectionUtil.isEmpty(providerList)) {
            throw new RenException(ErrorCode.MODEL_PROVIDER_NOT_EXIST);
        }
    
        // 保存供应器提供的模型
        ModelConfigEntity modelConfigEntity = ConvertUtils.sourceToTarget(modelConfigBodyDTO, ModelConfigEntity.class);
        modelConfigEntity.setModelType(modelType);
        modelConfigEntity.setIsDefault(0);
        modelConfigDao.insert(modelConfigEntity);
        
        // 返回数据前处理敏感字段
        ModelConfigDTO dto = ConvertUtils.sourceToTarget(modelConfigEntity, ModelConfigDTO.class);
        if (dto.getConfigJson() != null) {
            dto.setConfigJson(SensitiveDataUtils.maskSensitiveFields(dto.getConfigJson()));
        }
        
        return dto;
    }

    @Override
    public void delete(String id) {
        // 查看是否是默认
        ModelConfigEntity modelConfig = modelConfigDao.selectById(id);
        if (modelConfig != null && modelConfig.getIsDefault() == 1) {
            throw new RenException(ErrorCode.DEFAULT_MODEL_DELETE_ERROR);
        }
        // 验证是否有引用
        checkAgentReference(id);
        checkIntentConfigReference(id);

        modelConfigDao.deleteById(id);
    }

    /**
     * 检查智能体配置是否有引用
     * 
     * @param modelId 模型ID
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
     * 检查意图识别配置是否有引用
     * 
     * @param modelId 模型ID
     */
    private void checkIntentConfigReference(String modelId) {
        ModelConfigEntity modelConfig = modelConfigDao.selectById(modelId);
        if (modelConfig != null
                && "LLM".equals(modelConfig.getModelType() == null ? null : modelConfig.getModelType().toUpperCase())) {
            List<ModelConfigEntity> intentConfigs = modelConfigDao.selectList(
                    new QueryWrapper<ModelConfigEntity>()
                            .eq("model_type", "Intent")
                            .like("config_json", "%" + modelId + "%"));
            if (!intentConfigs.isEmpty()) {
                throw new RenException(ErrorCode.LLM_REFERENCED_BY_INTENT);
            }
        }
    }

    @Override
    public String getModelNameById(String id) {
        if (StringUtils.isBlank(id)) {
            return null;
        }

        String cachedName = (String) redisUtils.get(RedisKeys.getModelNameById(id));

        if (StringUtils.isNotBlank(cachedName)) {
            return cachedName;
        }

        ModelConfigEntity entity = modelConfigDao.selectById(id);
        if (entity != null) {
            String modelName = entity.getModelName();
            if (StringUtils.isNotBlank(modelName)) {
                redisUtils.set(RedisKeys.getModelNameById(id), modelName);
            }
            return modelName;
        }

        return null;
    }

    @Override
    public void setDefaultModel(String modelType, int isDefault) {
        ModelConfigEntity entity = new ModelConfigEntity();
        entity.setIsDefault(isDefault);
        modelConfigDao.update(entity, new QueryWrapper<ModelConfigEntity>()
                .eq("model_type", modelType));
    }

    @Override
    public ModelConfigEntity selectById(Serializable id) {
        ModelConfigEntity entity = super.selectById(id);
        if (entity != null && entity.getConfigJson() != null) {
            // 对配置中的敏感数据进行隐藏处理
            JSONObject maskedConfigJson = SensitiveDataUtils.maskSensitiveFields(entity.getConfigJson());
            entity.setConfigJson(maskedConfigJson);
        }
        return entity;
    }

    // 重写getPageData方法，添加敏感数据处理
    @Override
    protected <D> PageData<D> getPageData(IPage<?> page, Class<D> target) {
        List<?> records = page.getRecords();
        if (records != null && !records.isEmpty()) {
            for (Object record : records) {
                if (record instanceof ModelConfigEntity) {
                    ModelConfigEntity entity = (ModelConfigEntity) record;
                    if (entity.getConfigJson() != null) {
                        // 对配置中的敏感数据进行隐藏处理
                        JSONObject maskedConfigJson = SensitiveDataUtils.maskSensitiveFields(entity.getConfigJson());
                        entity.setConfigJson(maskedConfigJson);
                    }
                }
            }
        }
        return super.getPageData(page, target);
    }

    // 确保只有一个getModelById方法实现
    @Override
    public ModelConfigEntity getModelById(String id, boolean isCache) {
        ModelConfigEntity entity = null;
        if (isCache) {
            String cacheKey = RedisKeys.getModelConfigById(id);
            entity = (ModelConfigEntity) redisUtils.get(cacheKey);
            if (entity != null) {
                // 从缓存获取的数据也需要处理敏感信息
                if (entity.getConfigJson() != null) {
                    JSONObject maskedConfigJson = SensitiveDataUtils.maskSensitiveFields(entity.getConfigJson());
                    entity.setConfigJson(maskedConfigJson);
                }
                return entity;
            }
        }
        
        // 从数据库获取数据
        entity = modelConfigDao.selectById(id);
        if (entity != null) {
            // 处理敏感信息
            if (entity.getConfigJson() != null) {
                JSONObject maskedConfigJson = SensitiveDataUtils.maskSensitiveFields(entity.getConfigJson());
                entity.setConfigJson(maskedConfigJson);
            }
            
            if (isCache) {
                // 缓存处理后的对象
                redisUtils.set(RedisKeys.getModelConfigById(id), entity);
            }
        }
        return entity;
    }
}
