package xiaozhi.modules.knowledge.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import lombok.AllArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.beans.BeanUtils;
import xiaozhi.common.constant.Constant;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.page.PageData;
import xiaozhi.common.redis.RedisKeys;
import xiaozhi.common.redis.RedisUtils;
import xiaozhi.common.service.impl.BaseServiceImpl;
import xiaozhi.common.utils.ConvertUtils;
import xiaozhi.common.utils.JsonUtils;
import xiaozhi.common.utils.ToolUtil;
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

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * 知识库服务实现类 (Refactored)
 * 集成 RAGFlow Adapter 与 Shadow DB 模式
 */
@Service
@AllArgsConstructor
@Slf4j
public class KnowledgeBaseServiceImpl extends BaseServiceImpl<KnowledgeBaseDao, KnowledgeBaseEntity>
        implements KnowledgeBaseService {

    private final KnowledgeBaseDao knowledgeBaseDao;
    private final ModelConfigService modelConfigService;
    private final ModelConfigDao modelConfigDao;
    private final RedisUtils redisUtils;

    @Override
    @SuppressWarnings("deprecation")
    public PageData<KnowledgeBaseDTO> getPageList(KnowledgeBaseDTO knowledgeBaseDTO, Integer page, Integer limit) {
        Page<KnowledgeBaseEntity> pageInfo = new Page<>(page, limit);
        QueryWrapper<KnowledgeBaseEntity> queryWrapper = new QueryWrapper<>();

        if (knowledgeBaseDTO != null) {
            queryWrapper.like(StringUtils.isNotBlank(knowledgeBaseDTO.getName()), "name", knowledgeBaseDTO.getName());
            queryWrapper.eq(knowledgeBaseDTO.getStatus() != null, "status", knowledgeBaseDTO.getStatus());
            queryWrapper.eq("creator", knowledgeBaseDTO.getCreator());
        }
        queryWrapper.orderByDesc("created_at");

        IPage<KnowledgeBaseEntity> iPage = knowledgeBaseDao.selectPage(pageInfo, queryWrapper);
        PageData<KnowledgeBaseDTO> pageData = getPageData(iPage, KnowledgeBaseDTO.class);

        // Enrich with Document Count from RAG (Optional / Lazy)
        if (pageData != null && pageData.getList() != null) {
            for (KnowledgeBaseDTO dto : pageData.getList()) {
                enrichDocumentCount(dto);
            }
        }
        return pageData;
    }

    private void enrichDocumentCount(KnowledgeBaseDTO dto) {
        try {
            if (StringUtils.isNotBlank(dto.getDatasetId()) && StringUtils.isNotBlank(dto.getRagModelId())) {
                KnowledgeBaseAdapter adapter = getAdapterByModelId(dto.getRagModelId());
                if (adapter != null) {
                    dto.setDocumentCount(adapter.getDocumentCount(dto.getDatasetId()));
                }
            }
        } catch (Exception e) {
            log.warn("无法获取知识库 {} 的文档计数: {}", dto.getName(), e.getMessage());
            dto.setDocumentCount(0);
        }
    }

    @Override
    public KnowledgeBaseDTO getById(String id) {
        KnowledgeBaseEntity entity = knowledgeBaseDao.selectById(id);
        if (entity == null) {
            throw new RenException(ErrorCode.Knowledge_Base_RECORD_NOT_EXISTS);
        }
        return ConvertUtils.sourceToTarget(entity, KnowledgeBaseDTO.class);
    }

    @Override
    public KnowledgeBaseDTO getByDatasetId(String datasetId) {
        if (StringUtils.isBlank(datasetId)) {
            throw new RenException(ErrorCode.PARAMS_GET_ERROR);
        }
        KnowledgeBaseEntity entity = knowledgeBaseDao
                .selectOne(new QueryWrapper<KnowledgeBaseEntity>().eq("dataset_id", datasetId));
        if (entity == null) {
            throw new RenException(ErrorCode.Knowledge_Base_RECORD_NOT_EXISTS);
        }
        return ConvertUtils.sourceToTarget(entity, KnowledgeBaseDTO.class);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    @SuppressWarnings("deprecation")
    public KnowledgeBaseDTO save(KnowledgeBaseDTO dto) {
        // 1. Validation
        checkDuplicateName(dto.getName(), null);
        KnowledgeBaseAdapter adapter = null;

        // 2. RAG Creation
        String datasetId = null;
        try {
            // 若未指定 RAG 模型，自动使用系统默认
            if (StringUtils.isBlank(dto.getRagModelId())) {
                List<ModelConfigEntity> models = getRAGModels();
                if (models != null && !models.isEmpty()) {
                    dto.setRagModelId(models.get(0).getId());
                } else {
                    throw new RenException(ErrorCode.RAG_CONFIG_NOT_FOUND, "未指定且无可用默认 RAG 模型");
                }
            }

            Map<String, Object> ragConfig = getValidatedRAGConfig(dto.getRagModelId());
            adapter = KnowledgeBaseAdapterFactory.getAdapter((String) ragConfig.get("type"),
                    ragConfig);

            Map<String, Object> createParams = new HashMap<>();
            createParams.put("name", SecurityUser.getUser().getUsername() + "_" + dto.getName());
            if (StringUtils.isNotBlank(dto.getDescription())) {
                createParams.put("description", dto.getDescription());
            }

            Map<String, Object> ragResponse = adapter.createDataset(createParams);
            if (ragResponse == null || !ragResponse.containsKey("id")) {
                throw new RenException(ErrorCode.RAG_API_ERROR, "RAG创建返回无效: 缺失ID");
            }
            datasetId = (String) ragResponse.get("id");

            // 3. Local Save (Shadow)
            KnowledgeBaseEntity entity = ConvertUtils.sourceToTarget(dto, KnowledgeBaseEntity.class);

            entity.setId(null);

            entity.setDatasetId(datasetId);
            entity.setStatus(1); // Default Enabled

            // ✅ FULL PERSISTENCE: 严格全量回写 (User Requirement)
            if (ragResponse.containsKey("tenant_id")) {
                entity.setTenantId((String) ragResponse.get("tenant_id"));
            }
            if (ragResponse.containsKey("chunk_method")) {
                entity.setChunkMethod((String) ragResponse.get("chunk_method"));
            }
            if (ragResponse.containsKey("embedding_model")) {
                entity.setEmbeddingModel((String) ragResponse.get("embedding_model"));
            }
            if (ragResponse.containsKey("permission")) {
                entity.setPermission((String) ragResponse.get("permission"));
            }
            if (ragResponse.containsKey("avatar") && StringUtils.isBlank(entity.getAvatar())) {
                entity.setAvatar((String) ragResponse.get("avatar"));
            }
            // Parse Config (JSON)
            if (ragResponse.containsKey("parser_config")) {
                Object parserConfig = ragResponse.get("parser_config");
                entity.setParserConfig(JsonUtils.toJsonString(parserConfig));
            }
            // Numeric defaults
            if (ragResponse.containsKey("chunk_count")) {
                Object val = ragResponse.get("chunk_count");
                if (val instanceof Number)
                    entity.setChunkCount(((Number) val).longValue());
            } else {
                entity.setChunkCount(0L);
            }

            if (ragResponse.containsKey("document_count")) {
                Object val = ragResponse.get("document_count");
                if (val instanceof Number)
                    entity.setDocumentCount(((Number) val).longValue());
            } else {
                entity.setDocumentCount(0L);
            }

            // TokenNum (Default 0 as requested)
            entity.setTokenNum(0L);

            knowledgeBaseDao.insert(entity);
            return ConvertUtils.sourceToTarget(entity, KnowledgeBaseDTO.class);
        } catch (Exception e) {
            log.error("RAG创建或本地保存失败", e);
            // 如果datasetId已生成但在保存本地时失败，尝试回滚RAG (Best Effort)
            if (StringUtils.isNotBlank(datasetId)) {
                try {
                    if (adapter != null)
                        adapter.deleteDataset(datasetId);
                } catch (Exception rollbackEx) {
                    log.error("RAG回滚失败: {}", datasetId, rollbackEx);
                }
            }
            if (e instanceof RenException) {
                throw (RenException) e;
            }
            throw new RenException(ErrorCode.RAG_API_ERROR, "创建知识库失败: " + e.getMessage());
        }
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    @SuppressWarnings("deprecation")
    public KnowledgeBaseDTO update(KnowledgeBaseDTO dto) {
        KnowledgeBaseEntity entity = knowledgeBaseDao.selectById(dto.getId());
        if (entity == null)
            throw new RenException(ErrorCode.Knowledge_Base_RECORD_NOT_EXISTS);

        checkDuplicateName(dto.getName(), dto.getId());

        // 验证数据集ID是否与其他记录冲突
        if (StringUtils.isNotBlank(dto.getDatasetId())) {
            KnowledgeBaseEntity conflictEntity = knowledgeBaseDao.selectOne(
                    new QueryWrapper<KnowledgeBaseEntity>()
                            .eq("dataset_id", dto.getDatasetId())
                            .ne("id", dto.getId()));
            if (conflictEntity != null) {
                throw new RenException(ErrorCode.DB_RECORD_EXISTS);
            }
        }

        // RAG Update if needed
        if (StringUtils.isNotBlank(entity.getDatasetId()) && StringUtils.isNotBlank(dto.getRagModelId())) {
            try {
                // 🤖 AUTO-FILL: 若 DTO 未传 ragModelId (极少情况)，尝试复用 Entity 中的
                if (StringUtils.isBlank(dto.getRagModelId())) {
                    dto.setRagModelId(entity.getRagModelId());
                }

                KnowledgeBaseAdapter adapter = getAdapterByModelId(dto.getRagModelId());
                if (adapter != null) {
                    Map<String, Object> updateParams = new HashMap<>();
                    // 1. 必填/核心字段
                    updateParams.put("name", SecurityUser.getUser().getUsername() + "_" + dto.getName());

                    // 2. 修复回退：描述字段
                    if (dto.getDescription() != null) {
                        updateParams.put("description", dto.getDescription());
                    }

                    // 3. 增强：支持更多元数据同步
                    if (dto.getPermission() != null)
                        updateParams.put("permission", dto.getPermission());
                    if (dto.getAvatar() != null)
                        updateParams.put("avatar", dto.getAvatar());
                    if (dto.getChunkMethod() != null)
                        updateParams.put("chunk_method", dto.getChunkMethod());
                    if (dto.getEmbeddingModel() != null)
                        updateParams.put("embedding_model", dto.getEmbeddingModel());

                    // 4. 解析配置 (JSON String -> Object)
                    if (StringUtils.isNotBlank(dto.getParserConfig())) {
                        try {
                            Map<String, Object> configMap = JsonUtils.parseObject(dto.getParserConfig(), Map.class);
                            updateParams.put("parser_config", configMap);
                        } catch (Exception e) {
                            log.warn("解析 parser_config 失败，跳过同步", e);
                        }
                    }

                    adapter.updateDataset(entity.getDatasetId(), updateParams);
                    log.info("RAG更新成功: {}", entity.getDatasetId());
                }
            } catch (Exception e) {
                log.error("RAG更新失败", e);
                // 恢复事务一致性：RAG失败则整体回滚
                if (e instanceof RenException) {
                    throw (RenException) e;
                }
                throw new RenException(ErrorCode.RAG_API_ERROR, "RAG更新失败: " + e.getMessage());
            }
        }

        BeanUtils.copyProperties(dto, entity);
        knowledgeBaseDao.updateById(entity);

        // Clean cache
        redisUtils.delete(RedisKeys.getKnowledgeBaseCacheKey(entity.getId()));

        return ConvertUtils.sourceToTarget(entity, KnowledgeBaseDTO.class);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    @SuppressWarnings("deprecation")
    public void deleteByDatasetId(String datasetId) {
        if (StringUtils.isBlank(datasetId)) {
            throw new RenException(ErrorCode.PARAMS_GET_ERROR);
        }

        KnowledgeBaseEntity entity = knowledgeBaseDao
                .selectOne(new QueryWrapper<KnowledgeBaseEntity>().eq("dataset_id", datasetId));

        // 1. 恢复 404 校验：找不到记录抛异常
        if (entity == null) {
            log.warn("记录不存在，datasetId: {}", datasetId);
            throw new RenException(ErrorCode.Knowledge_Base_RECORD_NOT_EXISTS);
        }
        log.info("找到记录: ID={}, datasetId={}, ragModelId={}",
                entity.getId(), entity.getDatasetId(), entity.getRagModelId());

        // 2. RAG Delete (Strict Mode)
        // 恢复严格一致性：RAG 删除失败则抛出异常，触发事务回滚，不允许已删除本地但保留远程的脏数据
        boolean apiDeleteSuccess = false;
        if (StringUtils.isNotBlank(entity.getRagModelId()) && StringUtils.isNotBlank(entity.getDatasetId())) {
            try {
                KnowledgeBaseAdapter adapter = getAdapterByModelId(entity.getRagModelId());
                if (adapter != null) {
                    adapter.deleteDataset(datasetId);
                }
                apiDeleteSuccess = true;
            } catch (Exception e) {
                log.error("RAG删除失败，触发回滚", e);
                if (e instanceof RenException) {
                    throw (RenException) e;
                }
                throw new RenException(ErrorCode.RAG_API_ERROR, "RAG删除失败: " + e.getMessage());
            }
        } else {
            log.warn("datasetId或ragModelId为空，跳过RAG删除");
            apiDeleteSuccess = true; // 没有RAG数据集，视为成功
        }

        // 3. Local Delete (Safe Order)
        // 恢复正确顺序：先删子表 (Plugin Mapping)，再删主表 (Entity)
        if (apiDeleteSuccess) {
            log.info("开始删除ai_agent_plugin_mapping表中与知识库ID '{}' 相关的映射记录", entity.getId());
            log.info("开始删除关联数据, entityId: {}", entity.getId());
            knowledgeBaseDao.deletePluginMappingByKnowledgeBaseId(entity.getId());
            log.info("插件映射记录删除完成");
            int deleteCount = knowledgeBaseDao.deleteById(entity.getId());
            log.info("本地数据库删除结果: {}", deleteCount > 0 ? "成功" : "失败");
            redisUtils.delete(RedisKeys.getKnowledgeBaseCacheKey(entity.getId()));
        }
    }

    @Override
    public List<KnowledgeBaseDTO> getByDatasetIdList(List<String> datasetIdList) {
        // 1. 入参判空 (Match Old Logic)
        if (ToolUtil.isEmpty(datasetIdList)) {
            throw new RenException(ErrorCode.PARAMS_GET_ERROR);
        }

        List<KnowledgeBaseEntity> list = knowledgeBaseDao
                .selectList(new QueryWrapper<KnowledgeBaseEntity>().in("dataset_id", datasetIdList));

        // 2. 结果命中校验 (Match Old Logic)
        if (ToolUtil.isEmpty(list)) {
            throw new RenException(ErrorCode.Knowledge_Base_RECORD_NOT_EXISTS);
        }

        return ConvertUtils.sourceToTarget(list, KnowledgeBaseDTO.class);
    }

    @Override
    public Map<String, Object> getRAGConfig(String ragModelId) {
        return getValidatedRAGConfig(ragModelId);
    }

    @Override
    @SuppressWarnings("deprecation")
    public Map<String, Object> getRAGConfigByDatasetId(String datasetId) {
        KnowledgeBaseEntity entity = knowledgeBaseDao
                .selectOne(new QueryWrapper<KnowledgeBaseEntity>().eq("dataset_id", datasetId));
        if (entity == null || StringUtils.isBlank(entity.getRagModelId())) {
            throw new RenException(ErrorCode.RAG_CONFIG_NOT_FOUND);
        }
        return getRAGConfig(entity.getRagModelId());
    }

    @Override
    public List<ModelConfigEntity> getRAGModels() {
        return modelConfigDao.selectList(new QueryWrapper<ModelConfigEntity>()
                .select("id", "model_name", "config_json") // Explicitly select needed fields
                .eq("model_type", Constant.RAG_CONFIG_TYPE)
                .eq("is_enabled", 1)
                .orderByDesc("is_default")
                .orderByDesc("create_date"));
    }

    // --- Helpers ---

    private void checkDuplicateName(String name, String excludeId) {
        if (StringUtils.isBlank(name))
            return;
        QueryWrapper<KnowledgeBaseEntity> qw = new QueryWrapper<>();
        qw.eq("name", name).eq("creator", SecurityUser.getUserId());
        if (excludeId != null)
            qw.ne("id", excludeId);
        if (knowledgeBaseDao.selectCount(qw) > 0) {
            throw new RenException(ErrorCode.KNOWLEDGE_BASE_NAME_EXISTS);
        }
    }

    private KnowledgeBaseAdapter getAdapterByModelId(String modelId) {
        Map<String, Object> config = getValidatedRAGConfig(modelId);
        return KnowledgeBaseAdapterFactory.getAdapter((String) config.get("type"), config);
    }

    private Map<String, Object> getValidatedRAGConfig(String modelId) {
        ModelConfigEntity configEntity = modelConfigService.getModelByIdFromCache(modelId);
        if (configEntity == null || configEntity.getConfigJson() == null) {
            throw new RenException(ErrorCode.RAG_CONFIG_NOT_FOUND);
        }
        Map<String, Object> config = new HashMap<>(configEntity.getConfigJson());
        if (!config.containsKey("type")) {
            config.put("type", "ragflow");
        }
        return config;
    }
}