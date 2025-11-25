package xiaozhi.modules.knowledge.service.impl;

import java.io.IOException;
import java.io.Serializable;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.apache.commons.lang3.StringUtils;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.fasterxml.jackson.databind.ObjectMapper;

import lombok.AllArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import xiaozhi.common.constant.Constant;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.page.PageData;
import xiaozhi.common.redis.RedisKeys;
import xiaozhi.common.redis.RedisUtils;
import xiaozhi.common.service.impl.BaseServiceImpl;
import xiaozhi.common.utils.ConvertUtils;
import xiaozhi.common.utils.MessageUtils;
import xiaozhi.modules.knowledge.dao.KnowledgeBaseDao;
import xiaozhi.modules.knowledge.dto.KnowledgeBaseDTO;
import xiaozhi.modules.knowledge.entity.KnowledgeBaseEntity;
import xiaozhi.modules.knowledge.rag.KnowledgeBaseAdapter;
import xiaozhi.modules.knowledge.rag.KnowledgeBaseAdapterFactory;
import xiaozhi.modules.knowledge.service.KnowledgeBaseService;
import xiaozhi.modules.model.dao.ModelConfigDao;
import xiaozhi.modules.model.entity.ModelConfigEntity;
import xiaozhi.modules.model.service.ModelConfigService;
import xiaozhi.modules.security.user.SecurityUser;

@Service
@AllArgsConstructor
@Slf4j
public class KnowledgeBaseServiceImpl extends BaseServiceImpl<KnowledgeBaseDao, KnowledgeBaseEntity>
        implements KnowledgeBaseService {

    private final KnowledgeBaseDao knowledgeBaseDao;
    private final ModelConfigService modelConfigService;
    private final ModelConfigDao modelConfigDao;
    private final RedisUtils redisUtils;
    private RestTemplate restTemplate = new RestTemplate();
    private final ObjectMapper objectMapper = new ObjectMapper();

    @Override
    public KnowledgeBaseEntity selectById(Serializable datasetId) {
        if (datasetId == null) {
            return null;
        }

        // 先从Redis获取缓存
        String key = RedisKeys.getKnowledgeBaseCacheKey(datasetId.toString());
        KnowledgeBaseEntity cachedEntity = (KnowledgeBaseEntity) redisUtils.get(key);
        if (cachedEntity != null) {
            return cachedEntity;
        }

        // 如果缓存中没有，则从数据库获取
        KnowledgeBaseEntity entity = knowledgeBaseDao.selectById(datasetId);
        if (entity == null) {
            return null;
        }

        // 存入Redis缓存
        redisUtils.set(key, entity);

        return entity;
    }

    @Override
    public PageData<KnowledgeBaseDTO> getPageList(KnowledgeBaseDTO knowledgeBaseDTO, Integer page, Integer limit) {
        long curPage = page;
        long pageSize = limit;
        Page<KnowledgeBaseEntity> pageInfo = new Page<>(curPage, pageSize);

        QueryWrapper<KnowledgeBaseEntity> queryWrapper = new QueryWrapper<>();

        // 添加查询条件
        if (knowledgeBaseDTO != null) {
            queryWrapper.like(StringUtils.isNotBlank(knowledgeBaseDTO.getName()), "name", knowledgeBaseDTO.getName());
            queryWrapper.eq(knowledgeBaseDTO.getStatus() != null, "status", knowledgeBaseDTO.getStatus());
            queryWrapper.eq("creator", knowledgeBaseDTO.getCreator());
        }

        // 添加排序规则：按创建时间降序
        queryWrapper.orderByDesc("created_at");

        IPage<KnowledgeBaseEntity> knowledgeBaseEntityIPage = knowledgeBaseDao.selectPage(pageInfo, queryWrapper);

        // 获取分页数据
        PageData<KnowledgeBaseDTO> pageData = getPageData(knowledgeBaseEntityIPage, KnowledgeBaseDTO.class);

        // 为每个知识库获取文档数量
        if (pageData != null && pageData.getList() != null) {
            for (KnowledgeBaseDTO knowledgeBase : pageData.getList()) {
                try {
                    Integer documentCount = getDocumentCountFromRAG(knowledgeBase.getDatasetId(),
                            knowledgeBase.getRagModelId());
                    knowledgeBase.setDocumentCount(documentCount);
                } catch (Exception e) {
                    // 构建详细的错误信息，包含异常类型和消息
                    String baseErrorMessage = e.getClass().getSimpleName() + " - 获取知识库文档数量失败";
                    String errorMessage = baseErrorMessage + (e.getMessage() != null ? ": " + e.getMessage() : "");
                    log.warn("知识库 {} {}", knowledgeBase.getDatasetId(), errorMessage);
                    knowledgeBase.setDocumentCount(0); // 设置默认值
                }
            }
        }

        return pageData;
    }

    @Override
    public KnowledgeBaseDTO getById(String id) {
        if (StringUtils.isBlank(id)) {
            throw new RenException(ErrorCode.IDENTIFIER_NOT_NULL);
        }

        KnowledgeBaseEntity entity = knowledgeBaseDao.selectById(id);
        if (entity == null) {
            throw new RenException(ErrorCode.Knowledge_Base_RECORD_NOT_EXISTS);
        }

        return ConvertUtils.sourceToTarget(entity, KnowledgeBaseDTO.class);
    }

    @Override
    public KnowledgeBaseDTO save(KnowledgeBaseDTO knowledgeBaseDTO) {
        if (knowledgeBaseDTO == null) {
            throw new RenException(ErrorCode.PARAMS_GET_ERROR);
        }

        // 检查是否存在同名知识库
        checkDuplicateKnowledgeBaseName(knowledgeBaseDTO, null);

        String datasetId = null;
        // 调用RAG API创建数据集
        try {
            Map<String, Object> ragConfig = getValidatedRAGConfig(knowledgeBaseDTO.getRagModelId());
            datasetId = createDatasetInRAG(
                    knowledgeBaseDTO.getName(),
                    knowledgeBaseDTO.getDescription(),
                    ragConfig);
        } catch (Exception e) {
            // 如果RAG API调用失败，直接抛出异常
            throw e;
        }

        // 验证数据集ID是否已存在
        KnowledgeBaseEntity existingEntity = knowledgeBaseDao.selectOne(
                new QueryWrapper<KnowledgeBaseEntity>().eq("dataset_id", datasetId));
        if (existingEntity != null) {
            // 如果datasetId已存在，删除RAG中的数据集并抛出异常
            try {
                Map<String, Object> ragConfig = getValidatedRAGConfig(knowledgeBaseDTO.getRagModelId());
                deleteDatasetInRAG(datasetId, ragConfig);
            } catch (Exception deleteException) {
                // 提供更详细的错误信息，包括异常类型和消息
                String errorMessage = "删除重复datasetId的RAG数据集失败: " + deleteException.getClass().getSimpleName();
                if (deleteException.getMessage() != null) {
                    errorMessage += " - " + deleteException.getMessage();
                }
                log.warn(errorMessage, deleteException);
            }
            throw new RenException(ErrorCode.DB_RECORD_EXISTS);
        }

        // 创建本地实体并保存
        KnowledgeBaseEntity entity = ConvertUtils.sourceToTarget(knowledgeBaseDTO, KnowledgeBaseEntity.class);
        entity.setDatasetId(datasetId);
        knowledgeBaseDao.insert(entity);

        return ConvertUtils.sourceToTarget(entity, KnowledgeBaseDTO.class);
    }

    @Override
    public KnowledgeBaseDTO update(KnowledgeBaseDTO knowledgeBaseDTO) {
        if (knowledgeBaseDTO == null || StringUtils.isBlank(knowledgeBaseDTO.getId())) {
            throw new RenException(ErrorCode.IDENTIFIER_NOT_NULL);
        }

        // 检查记录是否存在
        KnowledgeBaseEntity existingEntity = knowledgeBaseDao.selectById(knowledgeBaseDTO.getId());
        if (existingEntity == null) {
            throw new RenException(ErrorCode.Knowledge_Base_RECORD_NOT_EXISTS);
        }

        // 检查是否存在同名知识库（排除当前记录）
        checkDuplicateKnowledgeBaseName(knowledgeBaseDTO, knowledgeBaseDTO.getId());

        // 验证数据集ID是否与其他记录冲突
        if (StringUtils.isNotBlank(knowledgeBaseDTO.getDatasetId())) {
            KnowledgeBaseEntity conflictEntity = knowledgeBaseDao.selectOne(
                    new QueryWrapper<KnowledgeBaseEntity>()
                            .eq("dataset_id", knowledgeBaseDTO.getDatasetId())
                            .ne("id", knowledgeBaseDTO.getId()));
            if (conflictEntity != null) {
                throw new RenException(ErrorCode.DB_RECORD_EXISTS);
            }
        }

        boolean needRagValidation = StringUtils.isNotBlank(knowledgeBaseDTO.getDatasetId())
                && StringUtils.isNotBlank(knowledgeBaseDTO.getRagModelId());

        if (needRagValidation) {
            try {
                // 先校验RAG配置
                Map<String, Object> ragConfig = getValidatedRAGConfig(knowledgeBaseDTO.getRagModelId());

                // 调用RAG API更新数据集
                updateDatasetInRAG(
                        knowledgeBaseDTO.getDatasetId(),
                        knowledgeBaseDTO.getName(),
                        knowledgeBaseDTO.getDescription(),
                        ragConfig);

                log.info("RAG API更新成功，datasetId: {}", knowledgeBaseDTO.getDatasetId());
            } catch (Exception e) {
                // 提供更详细的错误信息，包括异常类型和消息
                String errorMessage = "更新RAG数据集失败: " + e.getClass().getSimpleName();
                if (e.getMessage() != null) {
                    errorMessage += " - " + e.getMessage();
                }
                log.error(errorMessage, e);
                throw e;
            }
        } else {
            log.warn("datasetId或ragModelId为空，跳过RAG更新");
        }

        KnowledgeBaseEntity entity = ConvertUtils.sourceToTarget(knowledgeBaseDTO, KnowledgeBaseEntity.class);
        knowledgeBaseDao.updateById(entity);

        // 删除缓存
        if (entity.getDatasetId() != null) {
            redisUtils.delete(RedisKeys.getKnowledgeBaseCacheKey(entity.getId()));
        }

        return ConvertUtils.sourceToTarget(entity, KnowledgeBaseDTO.class);
    }

    @Override
    public KnowledgeBaseDTO getByDatasetId(String datasetId) {
        if (StringUtils.isBlank(datasetId)) {
            throw new RenException(ErrorCode.PARAMS_GET_ERROR);
        }

        KnowledgeBaseEntity entity = knowledgeBaseDao.selectOne(
                new QueryWrapper<KnowledgeBaseEntity>().eq("dataset_id", datasetId));

        if (entity == null) {
            throw new RenException(ErrorCode.Knowledge_Base_RECORD_NOT_EXISTS);
        }

        return ConvertUtils.sourceToTarget(entity, KnowledgeBaseDTO.class);
    }

    @Override
    public void deleteByDatasetId(String datasetId) {
        if (StringUtils.isBlank(datasetId)) {
            throw new RenException(ErrorCode.PARAMS_GET_ERROR);
        }

        log.info("=== 开始通过datasetId删除操作 ===");
        log.info("删除datasetId: {}", datasetId);

        KnowledgeBaseEntity entity = knowledgeBaseDao.selectOne(
                new QueryWrapper<KnowledgeBaseEntity>().eq("dataset_id", datasetId));

        if (entity == null) {
            log.warn("记录不存在，datasetId: {}", datasetId);
            throw new RenException(ErrorCode.Knowledge_Base_RECORD_NOT_EXISTS);
        }
        redisUtils.delete(RedisKeys.getKnowledgeBaseCacheKey(entity.getId()));

        log.info("找到记录: ID={}, datasetId={}, ragModelId={}",
                entity.getId(), entity.getDatasetId(), entity.getRagModelId());

        // 先调用RAG API删除数据集
        boolean apiDeleteSuccess = false;
        if (StringUtils.isNotBlank(entity.getDatasetId()) && StringUtils.isNotBlank(entity.getRagModelId())) {
            try {
                log.info("开始调用RAG API删除数据集");
                // 在删除前进行RAG配置校验
                Map<String, Object> ragConfig = getValidatedRAGConfig(entity.getRagModelId());
                deleteDatasetInRAG(entity.getDatasetId(), ragConfig);
                log.info("RAG API删除调用完成");
                apiDeleteSuccess = true;
            } catch (Exception e) {
                // 提供更详细的错误信息，包括异常类型和消息
                String errorMessage = "删除RAG数据集失败: " + e.getClass().getSimpleName();
                if (e.getMessage() != null) {
                    errorMessage += " - " + e.getMessage();
                }
                log.error(errorMessage, e);
                throw e;
            }
        } else {
            log.warn("datasetId或ragModelId为空，跳过RAG删除");
            apiDeleteSuccess = true; // 没有RAG数据集，视为成功
        }

        // API删除成功后再删除本地记录
        if (apiDeleteSuccess) {
            log.info("开始删除ai_agent_plugin_mapping表中与知识库ID '{}' 相关的映射记录", entity.getId());

            // 先删除相关的插件映射记录
            knowledgeBaseDao.deletePluginMappingByKnowledgeBaseId(entity.getId());
            log.info("插件映射记录删除完成");

            int deleteCount = knowledgeBaseDao.deleteById(entity.getId());
            log.info("本地数据库删除结果: {}", deleteCount > 0 ? "成功" : "失败");
        }

        log.info("=== 通过datasetId删除操作结束 ===");
    }

    @Override
    public Map<String, Object> getRAGConfig(String ragModelId) {
        if (StringUtils.isBlank(ragModelId)) {
            throw new RenException(ErrorCode.PARAMS_GET_ERROR);
        }

        // 从缓存获取模型配置
        ModelConfigEntity modelConfig = modelConfigService.getModelByIdFromCache(ragModelId);
        if (modelConfig == null || modelConfig.getConfigJson() == null) {
            throw new RenException(ErrorCode.RAG_CONFIG_NOT_FOUND);
        }

        // 验证是否为RAG类型配置
        if (!Constant.RAG_CONFIG_TYPE.equals(modelConfig.getModelType().toUpperCase())) {
            throw new RenException(ErrorCode.RAG_CONFIG_TYPE_ERROR);
        }

        Map<String, Object> config = modelConfig.getConfigJson();

        // 验证必要的配置参数
        validateRagConfig(config);

        // 返回配置信息
        return config;
    }

    @Override
    public Map<String, Object> getRAGConfigByDatasetId(String datasetId) {
        if (StringUtils.isBlank(datasetId)) {
            throw new RenException(ErrorCode.RAG_DATASET_ID_NOT_NULL);
        }

        // 根据datasetId查询知识库信息
        KnowledgeBaseDTO knowledgeBase = getByDatasetId(datasetId);
        if (knowledgeBase == null) {
            log.warn("未找到datasetId为{}的知识库", datasetId);
            throw new RenException(ErrorCode.Knowledge_Base_RECORD_NOT_EXISTS);
        }

        // 如果知识库指定了ragModelId，使用该配置
        String ragModelId = knowledgeBase.getRagModelId();
        if (StringUtils.isBlank(ragModelId)) {
            log.warn("知识库datasetId为{}未配置ragModelId", datasetId);
            throw new RenException(ErrorCode.RAG_CONFIG_NOT_FOUND);
        }

        // 获取并返回RAG配置
        return getRAGConfig(ragModelId);
    }

    @Override
    public List<Map<String, Object>> getRAGModels() {
        // 查询RAG类型的模型配置
        QueryWrapper<ModelConfigEntity> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("model_type", Constant.RAG_CONFIG_TYPE)
                .eq("is_enabled", 1)
                .orderByDesc("is_default")
                .orderByDesc("create_date");

        List<ModelConfigEntity> modelConfigs = modelConfigDao.selectList(queryWrapper);

        List<Map<String, Object>> modelList = new ArrayList<>();
        for (ModelConfigEntity modelConfig : modelConfigs) {
            Map<String, Object> modelInfo = new HashMap<>();
            modelInfo.put("id", modelConfig.getId());
            modelInfo.put("modelName", modelConfig.getModelName());
            modelList.add(modelInfo);
        }
        return modelList;
    }

    /**
     * 验证RAG配置中是否包含必要的参数
     */
    private void validateRagConfig(Map<String, Object> config) {
        if (config == null) {
            throw new RenException(ErrorCode.RAG_CONFIG_NOT_FOUND);
        }

        // 从配置中提取必要的参数
        String baseUrl = (String) config.get("base_url");
        String apiKey = (String) config.get("api_key");

        // 验证base_url是否存在且非空
        if (StringUtils.isBlank(baseUrl)) {
            throw new RenException(ErrorCode.RAG_API_ERROR_URL_NULL);
        }

        // 验证api_key是否存在且非空
        if (StringUtils.isBlank(apiKey)) {
            throw new RenException(ErrorCode.RAG_API_ERROR_API_KEY_NULL);
        }

        // 检查api_key是否包含占位符
        if (apiKey.contains("你")) {
            throw new RenException(ErrorCode.RAG_API_ERROR_API_KEY_INVALID);
        }

        // 验证base_url格式
        if (!baseUrl.startsWith("http://") && !baseUrl.startsWith("https://")) {
            throw new RenException(ErrorCode.RAG_API_ERROR_URL_INVALID);
        }
    }

    /**
     * 从RAG配置中提取适配器类型
     * 
     * @param config RAG配置
     * @return 适配器类型
     */
    private String extractAdapterType(Map<String, Object> config) {
        if (config == null) {
            throw new RenException(ErrorCode.RAG_CONFIG_NOT_FOUND);
        }

        // 从配置中提取适配器类型
        String adapterType = (String) config.get("type");

        // 验证适配器类型是否存在且非空
        if (StringUtils.isBlank(adapterType)) {
            throw new RenException(ErrorCode.RAG_ADAPTER_TYPE_NOT_FOUND);
        }

        // 验证适配器类型是否已注册
        if (!KnowledgeBaseAdapterFactory.isAdapterTypeRegistered(adapterType)) {
            throw new RenException(ErrorCode.RAG_ADAPTER_TYPE_NOT_SUPPORTED,
                    "不支持的适配器类型: " + adapterType);
        }

        return adapterType;
    }

    /**
     * 使用适配器创建数据集
     */
    private String createDatasetInRAG(String name, String description, Map<String, Object> ragConfig) {
        log.info("开始使用适配器创建数据集, name: {}", name);

        try {
            // 从RAG配置中提取适配器类型
            String adapterType = extractAdapterType(ragConfig);

            // 使用适配器工厂获取适配器实例
            KnowledgeBaseAdapter adapter = KnowledgeBaseAdapterFactory.getAdapter(adapterType, ragConfig);

            // 构建数据集创建参数
            Map<String, Object> createParams = new HashMap<>();
            String username = SecurityUser.getUser().getUsername();
            createParams.put("name", username + "_" + name);
            if (StringUtils.isNotBlank(description)) {
                createParams.put("description", description);
            }

            // 调用适配器的创建数据集方法
            String datasetId = adapter.createDataset(createParams);

            log.info("数据集创建成功，datasetId: {}", datasetId);
            return datasetId;

        } catch (Exception e) {
            // 直接传递底层适配器的详细错误信息
            log.error("创建数据集失败", e);
            if (e instanceof RenException) {
                throw (RenException) e;
            }
            throw new RenException(ErrorCode.RAG_API_ERROR, e.getMessage());
        }
    }

    /**
     * 使用适配器更新数据集
     */
    private void updateDatasetInRAG(String datasetId, String name, String description,
            Map<String, Object> ragConfig) {
        log.info("开始使用适配器更新数据集，datasetId: {}, name: {}", datasetId, name);

        try {
            // 从RAG配置中提取适配器类型
            String adapterType = extractAdapterType(ragConfig);

            // 使用适配器工厂获取适配器实例
            KnowledgeBaseAdapter adapter = KnowledgeBaseAdapterFactory.getAdapter(adapterType, ragConfig);

            // 构建数据集更新参数
            Map<String, Object> updateParams = new HashMap<>();
            String username = SecurityUser.getUser().getUsername();
            updateParams.put("name", username + "_" + name);
            if (StringUtils.isNotBlank(description)) {
                updateParams.put("description", description);
            }

            // 调用适配器的更新数据集方法
            adapter.updateDataset(datasetId, updateParams);

            log.info("数据集更新成功，datasetId: {}", datasetId);

        } catch (Exception e) {
            // 直接传递底层适配器的详细错误信息
            log.error("更新数据集失败", e);
            if (e instanceof RenException) {
                throw (RenException) e;
            }
            throw new RenException(ErrorCode.RAG_API_ERROR, e.getMessage());
        }
    }

    /**
     * 使用适配器删除数据集
     */
    private void deleteDatasetInRAG(String datasetId, Map<String, Object> ragConfig) {
        log.info("开始使用适配器删除数据集，datasetId: {}", datasetId);

        try {
            // 从RAG配置中提取适配器类型
            String adapterType = extractAdapterType(ragConfig);

            // 使用适配器工厂获取适配器实例
            KnowledgeBaseAdapter adapter = KnowledgeBaseAdapterFactory.getAdapter(adapterType, ragConfig);

            // 调用适配器的删除数据集方法
            adapter.deleteDataset(datasetId);

            log.info("数据集删除成功，datasetId: {}", datasetId);

        } catch (Exception e) {
            // 直接传递底层适配器的详细错误信息
            log.error("删除数据集失败", e);
            if (e instanceof RenException) {
                throw (RenException) e;
            }
            throw new RenException(ErrorCode.RAG_API_ERROR, e.getMessage());
        }
    }

    /**
     * 获取RAG配置并验证
     */
    private Map<String, Object> getValidatedRAGConfig(String ragModelId) {
        if (StringUtils.isBlank(ragModelId)) {
            throw new RenException(ErrorCode.RAG_MODEL_ID_NOT_NULL);
        }

        Map<String, Object> ragConfig = getRAGConfig(ragModelId);

        // 验证RAG配置参数
        validateRagConfig(ragConfig);

        return ragConfig;
    }

    /**
     * 检查是否存在同名知识库
     * 
     * @param knowledgeBaseDTO 知识库DTO
     * @param excludeId        排除的ID（更新时使用）
     */
    private void checkDuplicateKnowledgeBaseName(KnowledgeBaseDTO knowledgeBaseDTO, String excludeId) {
        if (StringUtils.isNotBlank(knowledgeBaseDTO.getName())) {
            Long currentUserId = SecurityUser.getUserId();
            QueryWrapper<KnowledgeBaseEntity> queryWrapper = new QueryWrapper<KnowledgeBaseEntity>()
                    .eq("name", knowledgeBaseDTO.getName())
                    .eq("creator", currentUserId);

            // 如果提供了排除ID，则排除该记录
            if (StringUtils.isNotBlank(excludeId)) {
                queryWrapper.ne("id", excludeId);
            }

            long count = knowledgeBaseDao.selectCount(queryWrapper);
            if (count > 0) {
                throw new RenException(ErrorCode.KNOWLEDGE_BASE_NAME_EXISTS,
                        MessageUtils.getMessage(ErrorCode.KNOWLEDGE_BASE_NAME_EXISTS));
            }
        }
    }

    /**
     * 从适配器获取知识库的文档数量
     */
    private Integer getDocumentCountFromRAG(String datasetId, String ragModelId) {
        if (StringUtils.isBlank(datasetId) || StringUtils.isBlank(ragModelId)) {
            log.warn("datasetId或ragModelId为空，无法获取文档数量");
            return 0;
        }

        log.info("开始获取知识库 {} 的文档数量", datasetId);

        try {
            // 获取RAG配置
            Map<String, Object> ragConfig = getValidatedRAGConfig(ragModelId);

            // 从RAG配置中提取适配器类型
            String adapterType = extractAdapterType(ragConfig);

            // 使用适配器工厂获取适配器实例
            KnowledgeBaseAdapter adapter = KnowledgeBaseAdapterFactory.getAdapter(adapterType, ragConfig);

            // 调用适配器的获取文档数量方法
            Integer documentCount = adapter.getDocumentCount(datasetId);

            log.info("获取知识库 {} 的文档数量成功: {}", datasetId, documentCount);
            return documentCount;

        } catch (Exception e) {
            // 构建详细的错误信息，包含异常类型和消息
            String baseErrorMessage = e.getClass().getSimpleName() + " - 获取知识库文档数量失败";
            String errorMessage = baseErrorMessage + (e.getMessage() != null ? ": " + e.getMessage() : "");
            log.error(errorMessage, e);
            return 0;
        }
    }

}