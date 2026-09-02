package xiaozhi.modules.agent.service.impl;

import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Date;
import java.util.HashMap;
import java.util.HexFormat;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.TreeMap;
import java.util.UUID;
import java.util.function.Function;
import java.util.stream.Collectors;

import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.core.metadata.OrderItem;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.repository.IRepository;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;

import lombok.AllArgsConstructor;
import xiaozhi.common.constant.Constant;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.page.PageData;
import xiaozhi.common.service.impl.BaseServiceImpl;
import xiaozhi.common.utils.JsonUtils;
import xiaozhi.modules.agent.dao.AgentDao;
import xiaozhi.modules.agent.dao.AgentSnapshotDao;
import xiaozhi.modules.agent.dao.AgentTagDao;
import xiaozhi.modules.agent.dao.AgentTagRelationDao;
import xiaozhi.modules.agent.dto.AgentSnapshotDataDTO;
import xiaozhi.modules.agent.dto.AgentSnapshotPageDTO;
import xiaozhi.modules.agent.dto.AgentSnapshotTagDTO;
import xiaozhi.modules.agent.dto.AgentUpdateDTO;
import xiaozhi.modules.agent.dto.ContextProviderDTO;
import xiaozhi.modules.agent.entity.AgentContextProviderEntity;
import xiaozhi.modules.agent.entity.AgentEntity;
import xiaozhi.modules.agent.entity.AgentPluginMapping;
import xiaozhi.modules.agent.entity.AgentSnapshotEntity;
import xiaozhi.modules.agent.entity.AgentTagEntity;
import xiaozhi.modules.agent.entity.AgentTagRelationEntity;
import xiaozhi.modules.agent.Enums.AgentSnapshotField;
import xiaozhi.modules.agent.service.AgentChatHistoryService;
import xiaozhi.modules.agent.service.AgentContextProviderService;
import xiaozhi.modules.agent.service.AgentPluginMappingService;
import xiaozhi.modules.agent.service.AgentSnapshotService;
import xiaozhi.modules.agent.service.AgentTagService;
import xiaozhi.modules.agent.vo.AgentInfoVO;
import xiaozhi.modules.agent.vo.AgentSnapshotVO;
import xiaozhi.modules.correctword.service.CorrectWordFileService;
import xiaozhi.modules.model.entity.ModelConfigEntity;
import xiaozhi.modules.model.service.ModelConfigService;
import xiaozhi.modules.security.user.SecurityUser;

@Service
@AllArgsConstructor
public class AgentSnapshotServiceImpl extends BaseServiceImpl<AgentSnapshotDao, AgentSnapshotEntity>
        implements AgentSnapshotService {
    private static final int MAX_SNAPSHOTS_PER_AGENT = 100;
    private static final int LEGACY_REDACTION_BATCH_SIZE = 100;
    private static final int CURRENT_REDACTION_VERSION = 2;
    private static final TypeReference<List<String>> STRING_LIST_TYPE = new TypeReference<>() {
    };
    private static final TypeReference<HashMap<String, Object>> PARAM_INFO_TYPE = new TypeReference<>() {
    };
    private static final TypeReference<Map<String, Object>> OBJECT_MAP_TYPE = new TypeReference<>() {
    };
    private static final ObjectMapper SNAPSHOT_OBJECT_MAPPER = new ObjectMapper()
            .configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);
    private static final String SECRET_PLACEHOLDER = "__SNAPSHOT_SECRET_REDACTED__";
    private static final String SOURCE_CONFIG = "config";
    private static final String SOURCE_CURRENT_BACKUP = "current";
    private static final String SOURCE_RESTORE_RESULT = "restore";

    private final AgentSnapshotDao agentSnapshotDao;
    private final AgentDao agentDao;
    private final AgentTagDao agentTagDao;
    private final AgentTagRelationDao agentTagRelationDao;
    private final AgentPluginMappingService agentPluginMappingService;
    private final AgentContextProviderService agentContextProviderService;
    private final AgentTagService agentTagService;
    private final AgentChatHistoryService agentChatHistoryService;
    private final ModelConfigService modelConfigService;
    private final CorrectWordFileService correctWordFileService;

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void createSnapshot(String agentId, String source) {
        lockAgent(agentId);
        AgentInfoVO agent = getAgentInfo(agentId);
        AgentSnapshotDataDTO snapshotData = buildSnapshotData(agent);
        AgentSnapshotEntity previousSnapshot = agentSnapshotDao.selectLatestSnapshot(agentId);
        List<String> changedFields;
        if (previousSnapshot == null) {
            changedFields = List.of("initial");
        } else {
            AgentSnapshotDataDTO previousData = parseSnapshotData(previousSnapshot.getSnapshotData());
            changedFields = getChangedFields(previousData, snapshotData);
        }
        if (changedFields.isEmpty()) {
            return;
        }

        insertSnapshot(agentId, agent.getUserId(), source, snapshotData, changedFields);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public PageData<AgentSnapshotVO> page(String agentId, AgentSnapshotPageDTO params) {
        AgentSnapshotPageDTO pageParams = params == null ? new AgentSnapshotPageDTO() : params;
        Page<AgentSnapshotEntity> page = new Page<>(pageParams.pageOrDefault(), pageParams.limitOrDefault());
        page.addOrder(OrderItem.desc("version_no"));
        IPage<AgentSnapshotEntity> result = agentSnapshotDao.selectPage(page,
                new QueryWrapper<AgentSnapshotEntity>()
                        .eq("agent_id", agentId)
                        .le(pageParams.getMaxVersionNo() != null, "version_no", pageParams.getMaxVersionNo()));
        List<AgentSnapshotVO> list = result.getRecords().stream()
                .map(entity -> toVO(entity, false))
                .toList();
        return new PageData<>(list, result.getTotal());
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public AgentSnapshotVO getSnapshot(String agentId, String snapshotId) {
        lockAgent(agentId);
        AgentSnapshotEntity entity = getSnapshotEntity(agentId, snapshotId);
        AgentSnapshotVO detail = toVO(entity, true);
        AgentSnapshotDataDTO currentData = buildSnapshotData(agentId);
        detail.setCurrentSnapshotData(redactSnapshotData(currentData));
        detail.setCurrentStateToken(buildCurrentStateToken(currentData));
        return detail;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void restoreSnapshot(String agentId, String snapshotId, String currentStateToken) {
        AgentEntity agent = agentDao.selectByIdForUpdate(agentId);
        if (agent == null) {
            throw new RenException(ErrorCode.AGENT_NOT_FOUND);
        }

        AgentSnapshotEntity snapshot = getSnapshotEntity(agentId, snapshotId);
        AgentSnapshotDataDTO data = parseSnapshotData(snapshot.getSnapshotData());
        if (data == null) {
            throw new RenException("快照数据为空，无法恢复");
        }

        AgentInfoVO currentAgent = getAgentInfo(agentId);
        AgentSnapshotDataDTO currentData = buildSnapshotData(currentAgent);
        if (!Objects.equals(buildCurrentStateToken(currentData), currentStateToken)) {
            throw new RenException("当前配置已变化，请重新打开恢复预览后再试");
        }
        AgentSnapshotDataDTO restoreData = preserveCurrentSensitiveValues(data, currentData);
        validateSensitiveRestoreIsReversible(currentData, restoreData);
        List<String> requestedChangedFields = getChangedFields(currentData, restoreData);
        if (requestedChangedFields.isEmpty()) {
            return;
        }

        AgentSnapshotEntity latestSnapshot = agentSnapshotDao.selectLatestSnapshot(agentId);
        AgentSnapshotDataDTO latestData = latestSnapshot == null
                ? null
                : parseSnapshotData(latestSnapshot.getSnapshotData());
        List<String> backupChangedFields = getChangedFields(latestData, currentData);
        boolean backupCreated = !backupChangedFields.isEmpty();
        if (backupCreated) {
            insertSnapshot(agentId, currentAgent.getUserId(), SOURCE_CURRENT_BACKUP, currentData,
                    backupChangedFields, null, null, false);
        }

        applyAgentFields(agent, restoreData);
        validateRestoreParams(agent);
        applyMemoryPolicy(agent);
        agent.setUpdater(SecurityUser.getUserId());
        agent.setUpdatedAt(new Date());
        int updatedRows = agentDao.updateSnapshotFields(agent);
        // The row was already locked and verified above. Some MySQL configurations report 0 changed rows
        // when a relation-only restore leaves all scalar columns (including second-precision updated_at) unchanged.
        if (updatedRows < 0 || updatedRows > 1) {
            throw new RenException("智能体快照恢复失败");
        }

        restoreFunctions(agentId, restoreData.getFunctions());
        restoreContextProviders(agentId, restoreData.getContextProviders());
        correctWordFileService.saveAgentCorrectWords(agentId, nullToEmpty(restoreData.getCorrectWordFileIds()));
        restoreTags(agentId, restoreData);

        AgentSnapshotDataDTO restoredData = buildSnapshotData(agentId);
        List<String> restoredChangedFields = getChangedFields(currentData, restoredData);
        if (!restoredChangedFields.isEmpty()) {
            insertSnapshot(agentId, currentAgent.getUserId(), SOURCE_RESTORE_RESULT, restoredData,
                    restoredChangedFields, snapshot.getId(), snapshot.getVersionNo(), false);
        }
        if (backupCreated || !restoredChangedFields.isEmpty()) {
            pruneSnapshots(agentId);
        }
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deleteSnapshot(String agentId, String snapshotId) {
        lockAgent(agentId);
        AgentSnapshotEntity entity = getSnapshotEntity(agentId, snapshotId);
        Integer maxVersionNo = agentSnapshotDao.selectMaxVersionNo(agentId);
        if (Objects.equals(entity.getVersionNo(), maxVersionNo)) {
            throw new RenException("最新历史版本不能删除");
        }
        deleteById(snapshotId);
    }

    @Override
    public Integer getCurrentVersionNo(String agentId) {
        Integer maxVersionNo = agentSnapshotDao.selectMaxVersionNo(agentId);
        return maxVersionNo == null ? 0 : maxVersionNo;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deleteByAgentId(String agentId) {
        agentSnapshotDao.delete(new QueryWrapper<AgentSnapshotEntity>().eq("agent_id", agentId));
    }

    @Override
    public long redactLegacySnapshots() {
        String afterId = null;
        long migrated = 0;
        while (true) {
            List<AgentSnapshotEntity> batch = agentSnapshotDao.selectLegacyRedactionBatch(afterId,
                    LEGACY_REDACTION_BATCH_SIZE, CURRENT_REDACTION_VERSION);
            if (batch == null || batch.isEmpty()) {
                return migrated;
            }
            for (AgentSnapshotEntity snapshot : batch) {
                Map<String, Object> rawData = JsonUtils.parseObject(snapshot.getSnapshotData(), OBJECT_MAP_TYPE);
                if (rawData == null) {
                    throw new RenException("历史快照数据无法解析，已中止脱敏迁移: " + snapshot.getId());
                }
                snapshot.setSnapshotData(JsonUtils.toJsonString(redactSensitiveMap(rawData)));
            }
            int affected = agentSnapshotDao.updateRedactedSnapshots(batch, CURRENT_REDACTION_VERSION);
            if (affected < 0 || affected > batch.size()) {
                throw new RenException("历史快照批量脱敏迁移失败");
            }
            migrated += affected;
            afterId = batch.get(batch.size() - 1).getId();
        }
    }

    private void insertSnapshot(String agentId, Long userId, String source, AgentSnapshotDataDTO snapshotData,
            List<String> changedFields) {
        insertSnapshot(agentId, userId, source, snapshotData, changedFields, null, null);
    }

    private void insertSnapshot(String agentId, Long userId, String source, AgentSnapshotDataDTO snapshotData,
            List<String> changedFields, String restoreFromSnapshotId, Integer restoreFromVersionNo) {
        insertSnapshot(agentId, userId, source, snapshotData, changedFields, restoreFromSnapshotId,
                restoreFromVersionNo, true);
    }

    private void insertSnapshot(String agentId, Long userId, String source, AgentSnapshotDataDTO snapshotData,
            List<String> changedFields, String restoreFromSnapshotId, Integer restoreFromVersionNo,
            boolean pruneAfterInsert) {
        AgentSnapshotEntity entity = new AgentSnapshotEntity();
        entity.setId(UUID.randomUUID().toString().replace("-", ""));
        entity.setAgentId(agentId);
        entity.setUserId(userId);
        entity.setSnapshotData(JsonUtils.toJsonString(redactSnapshotData(snapshotData)));
        entity.setChangedFields(JsonUtils.toJsonString(changedFields));
        entity.setSource(StringUtils.defaultIfBlank(source, SOURCE_CONFIG));
        entity.setRestoreFromSnapshotId(restoreFromSnapshotId);
        entity.setRestoreFromVersionNo(restoreFromVersionNo);
        entity.setCreator(SecurityUser.getUserId());
        entity.setCreatedAt(new Date());
        entity.setRedactionVersion(CURRENT_REDACTION_VERSION);
        int inserted = agentSnapshotDao.insertWithNextVersion(entity);
        if (inserted != 1) {
            throw new RenException("快照版本号生成失败");
        }
        if (pruneAfterInsert) {
            pruneSnapshots(agentId);
        }
    }

    private void lockAgent(String agentId) {
        if (agentDao.selectByIdForUpdate(agentId) == null) {
            throw new RenException(ErrorCode.AGENT_NOT_FOUND);
        }
    }

    private void pruneSnapshots(String agentId) {
        agentSnapshotDao.deleteOlderThanKeepLimit(agentId, MAX_SNAPSHOTS_PER_AGENT);
    }

    private AgentSnapshotEntity getSnapshotEntity(String agentId, String snapshotId) {
        AgentSnapshotEntity entity = selectById(snapshotId);
        if (entity == null || !Objects.equals(agentId, entity.getAgentId())) {
            throw new RenException("快照不存在");
        }
        return entity;
    }

    private AgentInfoVO getAgentInfo(String agentId) {
        AgentInfoVO agent = agentDao.selectAgentInfoById(agentId);
        if (agent == null) {
            throw new RenException(ErrorCode.AGENT_NOT_FOUND);
        }
        return agent;
    }

    private AgentSnapshotDataDTO buildSnapshotData(String agentId) {
        return buildSnapshotData(getAgentInfo(agentId));
    }

    private AgentSnapshotDataDTO buildSnapshotData(AgentInfoVO agent) {
        AgentSnapshotDataDTO data = new AgentSnapshotDataDTO();
        data.setAgentCode(agent.getAgentCode());
        data.setAgentName(agent.getAgentName());
        data.setAsrModelId(agent.getAsrModelId());
        data.setVadModelId(agent.getVadModelId());
        data.setLlmModelId(agent.getLlmModelId());
        data.setSlmModelId(agent.getSlmModelId());
        data.setVllmModelId(agent.getVllmModelId());
        data.setTtsModelId(agent.getTtsModelId());
        data.setTtsVoiceId(agent.getTtsVoiceId());
        data.setTtsLanguage(agent.getTtsLanguage());
        data.setTtsVolume(agent.getTtsVolume());
        data.setTtsRate(agent.getTtsRate());
        data.setTtsPitch(agent.getTtsPitch());
        data.setMemModelId(agent.getMemModelId());
        data.setIntentModelId(agent.getIntentModelId());
        data.setChatHistoryConf(agent.getChatHistoryConf());
        data.setSystemPrompt(agent.getSystemPrompt());
        data.setSummaryMemory(agent.getSummaryMemory());
        data.setLangCode(agent.getLangCode());
        data.setLanguage(agent.getLanguage());
        data.setSort(agent.getSort());
        data.setFunctions(toFunctionInfo(agent.getFunctions()));
        data.setContextProviders(getContextProviders(agent.getId()));
        data.setCorrectWordFileIds(nullToEmpty(correctWordFileService.getAgentCorrectWordFileIds(agent.getId())));
        List<AgentSnapshotTagDTO> tags = getSnapshotTags(agent.getId());
        data.setTags(tags);
        data.setTagNames(tags.stream().map(AgentSnapshotTagDTO::getTagName).toList());
        return data;
    }

    private List<AgentSnapshotTagDTO> getSnapshotTags(String agentId) {
        List<AgentTagEntity> tags = agentTagDao.selectByAgentId(agentId);
        if (tags == null || tags.isEmpty()) {
            return Collections.emptyList();
        }
        List<AgentSnapshotTagDTO> snapshotTags = new ArrayList<>();
        for (int i = 0; i < tags.size(); i++) {
            AgentTagEntity tag = tags.get(i);
            AgentSnapshotTagDTO snapshotTag = new AgentSnapshotTagDTO();
            snapshotTag.setId(tag.getId());
            snapshotTag.setTagName(tag.getTagName());
            snapshotTag.setSort(i);
            snapshotTags.add(snapshotTag);
        }
        return snapshotTags;
    }

    private List<AgentUpdateDTO.FunctionInfo> toFunctionInfo(List<AgentPluginMapping> mappings) {
        if (mappings == null || mappings.isEmpty()) {
            return Collections.emptyList();
        }
        return mappings.stream().map(mapping -> {
            AgentUpdateDTO.FunctionInfo info = new AgentUpdateDTO.FunctionInfo();
            info.setPluginId(mapping.getPluginId());
            info.setParamInfo(parseParamInfo(mapping.getParamInfo()));
            return info;
        }).toList();
    }

    private HashMap<String, Object> parseParamInfo(String paramInfo) {
        if (StringUtils.isBlank(paramInfo)) {
            return new HashMap<>();
        }
        return JsonUtils.parseObject(paramInfo, PARAM_INFO_TYPE);
    }

    private List<xiaozhi.modules.agent.dto.ContextProviderDTO> getContextProviders(String agentId) {
        AgentContextProviderEntity contextEntity = agentContextProviderService.getByAgentId(agentId);
        if (contextEntity == null || contextEntity.getContextProviders() == null) {
            return Collections.emptyList();
        }
        return contextEntity.getContextProviders();
    }

    private List<String> getChangedFields(AgentSnapshotDataDTO current, AgentUpdateDTO pendingUpdate) {
        if (pendingUpdate == null) {
            return List.of("restore");
        }

        List<String> fields = new ArrayList<>();
        for (AgentSnapshotField field : AgentSnapshotField.values()) {
            Object nextValue = field.updateValue(pendingUpdate);
            if (nextValue != null && isChanged(field, field.snapshotValue(current), nextValue)) {
                fields.add(field.getFieldName());
            }
        }
        return fields;
    }

    private List<String> getChangedFields(AgentSnapshotDataDTO current, AgentSnapshotDataDTO next) {
        if (next == null) {
            return List.of("restore");
        }
        if (current == null) {
            current = new AgentSnapshotDataDTO();
        }

        List<String> fields = new ArrayList<>();
        for (AgentSnapshotField field : AgentSnapshotField.values()) {
            if (isChanged(field, field.snapshotValue(current), field.snapshotValue(next))) {
                fields.add(field.getFieldName());
            }
        }
        return fields;
    }

    private String buildCurrentStateToken(AgentSnapshotDataDTO data) {
        Map<String, Object> normalized = new TreeMap<>();
        for (AgentSnapshotField field : AgentSnapshotField.values()) {
            normalized.put(field.getFieldName(), normalizeForCompare(field, field.snapshotValue(data)));
        }
        byte[] payload = JsonUtils.toJsonString(normalized).getBytes(StandardCharsets.UTF_8);
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(payload));
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException("SHA-256 is unavailable", exception);
        }
    }

    private boolean isChanged(AgentSnapshotField field, Object current, Object next) {
        return !Objects.equals(normalizeForCompare(field, current), normalizeForCompare(field, next));
    }

    @SuppressWarnings("unchecked")
    private Object normalizeForCompare(AgentSnapshotField field, Object value) {
        return switch (field) {
            case FUNCTIONS -> normalizeFunctions((List<AgentUpdateDTO.FunctionInfo>) value);
            case CONTEXT_PROVIDERS -> normalizeJsonList((List<?>) value);
            case CORRECT_WORD_FILE_IDS -> normalizeStringList((List<String>) value);
            case TAG_NAMES -> normalizeStringList((List<String>) value);
            case SUMMARY_MEMORY -> normalizeBlankText(value);
            default -> value;
        };
    }

    private String normalizeBlankText(Object value) {
        if (value == null) {
            return "";
        }
        String text = String.valueOf(value);
        return StringUtils.isBlank(text) ? "" : text;
    }

    private Map<String, Object> normalizeFunctions(List<AgentUpdateDTO.FunctionInfo> functions) {
        Map<String, Object> result = new TreeMap<>();
        if (functions == null) {
            return result;
        }
        for (AgentUpdateDTO.FunctionInfo function : functions) {
            if (function == null || StringUtils.isBlank(function.getPluginId())) {
                continue;
            }
            result.put(function.getPluginId(), normalizeMap(function.getParamInfo()));
        }
        return result;
    }

    private List<String> normalizeStringList(List<String> values) {
        if (values == null) {
            return Collections.emptyList();
        }
        return values.stream()
                .filter(StringUtils::isNotBlank)
                .sorted()
                .toList();
    }

    private <T> List<String> normalizeJsonList(List<T> values) {
        if (values == null) {
            return Collections.emptyList();
        }
        return values.stream()
                .filter(Objects::nonNull)
                .map(value -> JsonUtils.toJsonString(normalizeValue(value)))
                .toList();
    }

    private Object normalizeValue(Object value) {
        return normalizeValue(value, null);
    }

    private Object normalizeValue(Object value, String parentKey) {
        if (value == null) {
            return null;
        }
        if (value instanceof CharSequence text && shouldTreatAsUrl(parentKey, text.toString())) {
            return normalizeUrlForCompare(text.toString(), parentKey);
        }
        if (value instanceof Map<?, ?> map) {
            return normalizeMap(map, parentKey);
        }
        if (value instanceof List<?> list) {
            return list.stream().map(item -> normalizeValue(item, parentKey)).toList();
        }
        if (isScalarValue(value)) {
            return value;
        }
        return normalizeMap(JsonUtils.parseObject(JsonUtils.toJsonString(value), OBJECT_MAP_TYPE), parentKey);
    }

    private boolean isScalarValue(Object value) {
        return value instanceof CharSequence
                || value instanceof Number
                || value instanceof Boolean
                || value instanceof Character
                || value instanceof Enum<?>
                || value instanceof Date;
    }

    private Map<String, Object> normalizeMap(Map<?, ?> map) {
        return normalizeMap(map, null);
    }

    private Map<String, Object> normalizeMap(Map<?, ?> map, String parentSemanticKey) {
        Map<String, Object> result = new TreeMap<>();
        if (map == null) {
            return result;
        }
        String structuredSensitiveKey = getStructuredSensitiveKey(map);
        map.forEach((key, value) -> {
            if (key != null) {
                String keyText = String.valueOf(key);
                String semanticKey = resolveUrlSemanticKey(parentSemanticKey, keyText);
                if (isSensitiveKey(keyText)
                        || (structuredSensitiveKey != null && "value".equalsIgnoreCase(keyText))) {
                    result.put(keyText, SECRET_PLACEHOLDER);
                } else if (value instanceof CharSequence text && shouldTreatAsUrl(semanticKey, text.toString())) {
                    result.put(keyText, normalizeUrlForCompare(text.toString(), semanticKey));
                } else {
                    result.put(keyText, normalizeValue(value, semanticKey));
                }
            }
        });
        return result;
    }

    private void applyAgentFields(AgentEntity agent, AgentSnapshotDataDTO data) {
        for (AgentSnapshotField field : AgentSnapshotField.values()) {
            field.applyTo(agent, data);
        }
    }

    private void validateRestoreParams(AgentEntity agent) {
        if (agent == null || StringUtils.isBlank(agent.getLlmModelId())) {
            return;
        }

        ModelConfigEntity llmModelData = modelConfigService.selectById(agent.getLlmModelId());
        if (llmModelData == null || llmModelData.getConfigJson() == null) {
            throw new RenException(ErrorCode.LLM_INTENT_PARAMS_MISMATCH);
        }
        Object typeValue = llmModelData.getConfigJson().get("type");
        String type = typeValue == null ? "" : typeValue.toString();
        if ("openai".equals(type) || "ollama".equals(type)) {
            return;
        }
        if ("Intent_function_call".equals(agent.getIntentModelId())) {
            throw new RenException(ErrorCode.LLM_INTENT_PARAMS_MISMATCH);
        }
    }

    private void applyMemoryPolicy(AgentEntity agent) {
        if (agent == null || StringUtils.isBlank(agent.getMemModelId())) {
            return;
        }
        if (Constant.MEMORY_NO_MEM.equals(agent.getMemModelId())) {
            agentChatHistoryService.deleteByAgentId(agent.getId(), true, true);
            agent.setSummaryMemory("");
        } else if (Constant.MEMORY_MEM_REPORT_ONLY.equals(agent.getMemModelId())) {
            agent.setSummaryMemory("");
        }
    }

    private void restoreFunctions(String agentId, List<AgentUpdateDTO.FunctionInfo> functions) {
        agentPluginMappingService.deleteByAgentId(agentId);
        if (functions == null || functions.isEmpty()) {
            return;
        }
        List<AgentPluginMapping> mappings = functions.stream().map(info -> {
            AgentPluginMapping mapping = new AgentPluginMapping();
            mapping.setAgentId(agentId);
            mapping.setPluginId(info.getPluginId());
            mapping.setParamInfo(JsonUtils.toJsonString(info.getParamInfo()));
            return mapping;
        }).toList();
        agentPluginMappingService.saveBatch(mappings, IRepository.DEFAULT_BATCH_SIZE);
    }

    private void restoreContextProviders(String agentId,
            List<xiaozhi.modules.agent.dto.ContextProviderDTO> contextProviders) {
        AgentContextProviderEntity entity = new AgentContextProviderEntity();
        entity.setAgentId(agentId);
        entity.setContextProviders(nullToEmpty(contextProviders));
        entity.setUpdater(SecurityUser.getUserId());
        entity.setUpdatedAt(new Date());
        agentContextProviderService.saveOrUpdateByAgentId(entity);
    }

    private void restoreTags(String agentId, AgentSnapshotDataDTO data) {
        List<AgentSnapshotTagDTO> tags = data.getTags();
        if (tags == null || tags.isEmpty()) {
            agentTagService.saveAgentTags(agentId, null, nullToEmpty(data.getTagNames()));
            return;
        }

        agentTagRelationDao.deleteByAgentId(agentId);
        List<AgentTagRelationEntity> relations = new ArrayList<>();
        Date now = new Date();
        for (int i = 0; i < tags.size(); i++) {
            AgentSnapshotTagDTO snapshotTag = tags.get(i);
            String tagId = restoreTag(snapshotTag, now);
            if (StringUtils.isBlank(tagId)) {
                continue;
            }
            AgentTagRelationEntity relation = new AgentTagRelationEntity();
            relation.setId(UUID.randomUUID().toString().replace("-", ""));
            relation.setAgentId(agentId);
            relation.setTagId(tagId);
            relation.setSort(i);
            relation.setCreator(SecurityUser.getUserId());
            relation.setCreatedAt(now);
            relation.setUpdater(SecurityUser.getUserId());
            relation.setUpdatedAt(now);
            relations.add(relation);
        }
        if (!relations.isEmpty()) {
            agentTagRelationDao.batchInsertRelation(relations);
        }
    }

    private String restoreTag(AgentSnapshotTagDTO snapshotTag, Date now) {
        if (snapshotTag == null || StringUtils.isBlank(snapshotTag.getTagName())) {
            return null;
        }

        AgentTagEntity tag = null;
        if (StringUtils.isNotBlank(snapshotTag.getId())) {
            tag = agentTagDao.selectById(snapshotTag.getId());
        }
        if (tag == null) {
            tag = agentTagDao.selectOne(new QueryWrapper<AgentTagEntity>()
                    .eq("tag_name", snapshotTag.getTagName())
                    .last("LIMIT 1"));
        }
        if (tag != null) {
            if (Objects.equals(tag.getDeleted(), 1)) {
                // Tags are global records shared by every agent that references them. Restoring a
                // snapshot must not revive a globally deleted tag as a side effect for other agents
                // (or tenants); require the user to recreate/select an active tag explicitly.
                throw new RenException("快照引用的标签已被删除，无法恢复，请先重新创建或选择标签");
            }
            return tag.getId();
        }

        AgentTagEntity newTag = new AgentTagEntity();
        newTag.setId(UUID.randomUUID().toString().replace("-", ""));
        newTag.setTagName(snapshotTag.getTagName());
        newTag.setSort(snapshotTag.getSort() == null ? 0 : snapshotTag.getSort());
        newTag.setDeleted(0);
        newTag.setCreator(SecurityUser.getUserId());
        newTag.setCreatedAt(now);
        newTag.setUpdater(SecurityUser.getUserId());
        newTag.setUpdatedAt(now);
        agentTagDao.insert(newTag);
        return newTag.getId();
    }

    private AgentSnapshotVO toVO(AgentSnapshotEntity entity, boolean includeData) {
        AgentSnapshotVO vo = new AgentSnapshotVO();
        vo.setId(entity.getId());
        vo.setAgentId(entity.getAgentId());
        vo.setUserId(entity.getUserId());
        vo.setVersionNo(entity.getVersionNo());
        vo.setChangedFields(parseChangedFields(entity.getChangedFields()));
        vo.setFieldOrder(AgentSnapshotField.names());
        vo.setSource(entity.getSource());
        vo.setRestoreFromSnapshotId(entity.getRestoreFromSnapshotId());
        vo.setRestoreFromVersionNo(entity.getRestoreFromVersionNo());
        vo.setCreator(entity.getCreator());
        vo.setCreatedAt(entity.getCreatedAt());
        if (includeData) {
            vo.setSnapshotData(redactSnapshotData(parseSnapshotData(entity.getSnapshotData())));
            vo.setAfterSnapshotData(redactSnapshotData(getAfterSnapshotData(entity)));
        }
        return vo;
    }

    private AgentSnapshotDataDTO getAfterSnapshotData(AgentSnapshotEntity entity) {
        AgentSnapshotEntity nextSnapshot = agentSnapshotDao.selectNextSnapshot(entity.getAgentId(), entity.getVersionNo());
        if (nextSnapshot != null) {
            return parseSnapshotData(nextSnapshot.getSnapshotData());
        }
        return null;
    }

    private List<String> parseChangedFields(String changedFields) {
        if (StringUtils.isBlank(changedFields)) {
            return Collections.emptyList();
        }
        return JsonUtils.parseObject(changedFields, STRING_LIST_TYPE);
    }

    /**
     * Snapshot payloads outlive the application version that wrote them. Keep
     * forward-compatible deserialization local to this persistence boundary so
     * unrelated API DTOs retain the project's normal unknown-field validation.
     * Unknown fields are intentionally ignored here; they are not restored by
     * this older application version.
     */
    private AgentSnapshotDataDTO parseSnapshotData(String value) {
        if (StringUtils.isBlank(value)) {
            return null;
        }
        try {
            return SNAPSHOT_OBJECT_MAPPER.readValue(value, AgentSnapshotDataDTO.class);
        } catch (Exception exception) {
            throw new RenException("快照数据无法解析");
        }
    }

    private AgentSnapshotDataDTO redactSnapshotData(AgentSnapshotDataDTO data) {
        if (data == null) {
            return null;
        }
        AgentSnapshotDataDTO copy = parseSnapshotData(JsonUtils.toJsonString(data));
        if (copy.getFunctions() != null) {
            copy.getFunctions().forEach(function -> {
                if (function != null) {
                    function.setParamInfo(redactSensitiveMap(function.getParamInfo()));
                }
            });
        }
        if (copy.getContextProviders() != null) {
            copy.getContextProviders().forEach(provider -> {
                if (provider != null) {
                    provider.setUrl(redactSensitiveUrl(provider.getUrl(), "url"));
                    provider.setHeaders(redactSensitiveMap(provider.getHeaders()));
                }
            });
        }
        return copy;
    }

    private AgentSnapshotDataDTO preserveCurrentSensitiveValues(AgentSnapshotDataDTO target, AgentSnapshotDataDTO current) {
        if (target == null) {
            return null;
        }
        AgentSnapshotDataDTO copy = parseSnapshotData(JsonUtils.toJsonString(target));
        Map<String, AgentUpdateDTO.FunctionInfo> currentFunctions = nullToEmpty(current == null ? null : current.getFunctions())
                .stream()
                .filter(function -> function != null && StringUtils.isNotBlank(function.getPluginId()))
                .collect(Collectors.toMap(AgentUpdateDTO.FunctionInfo::getPluginId, Function.identity(),
                        (left, right) -> left));
        if (copy.getFunctions() != null) {
            copy.getFunctions().forEach(function -> {
                if (function == null) {
                    return;
                }
                AgentUpdateDTO.FunctionInfo currentFunction = currentFunctions.get(function.getPluginId());
                function.setParamInfo(preserveCurrentSensitiveMap(function.getParamInfo(),
                        currentFunction == null ? null : currentFunction.getParamInfo()));
            });
        }

        copy.setContextProviders(preserveCurrentContextProviders(copy.getContextProviders(),
                current == null ? null : current.getContextProviders()));
        return copy;
    }

    private void validateSensitiveRestoreIsReversible(AgentSnapshotDataDTO current,
            AgentSnapshotDataDTO restored) {
        try {
            // Simulate restoring the automatic pre-restore backup from the proposed
            // result. If a current secret-bearing slot disappears, the reverse
            // preservation fails because snapshots intentionally never store secrets.
            preserveCurrentSensitiveValues(current, restored);
        } catch (RenException exception) {
            throw new RenException("目标版本会移除无法写入历史的敏感配置，请先手动处理相关密钥后再恢复");
        }
    }

    private HashMap<String, Object> redactSensitiveMap(Map<?, ?> map) {
        return redactSensitiveMap(map, null);
    }

    private HashMap<String, Object> redactSensitiveMap(Map<?, ?> map, String parentSemanticKey) {
        HashMap<String, Object> result = new HashMap<>();
        if (map == null) {
            return result;
        }
        String structuredSensitiveKey = getStructuredSensitiveKey(map);
        map.forEach((key, value) -> {
            if (key != null) {
                String keyText = String.valueOf(key);
                String semanticKey = resolveUrlSemanticKey(parentSemanticKey, keyText);
                if (isSensitiveKey(keyText)
                        || (structuredSensitiveKey != null && "value".equalsIgnoreCase(keyText))) {
                    result.put(keyText, SECRET_PLACEHOLDER);
                } else if (value instanceof CharSequence text && shouldTreatAsUrl(semanticKey, text.toString())) {
                    result.put(keyText, redactSensitiveUrl(text.toString(), semanticKey));
                } else {
                    result.put(keyText, redactSensitiveValue(value, semanticKey));
                }
            }
        });
        return result;
    }

    private Object redactSensitiveValue(Object value) {
        return redactSensitiveValue(value, null);
    }

    private Object redactSensitiveValue(Object value, String parentKey) {
        if (value instanceof CharSequence text && shouldTreatAsUrl(parentKey, text.toString())) {
            return redactSensitiveUrl(text.toString(), parentKey);
        }
        if (value instanceof Map<?, ?> map) {
            return redactSensitiveMap(map, parentKey);
        }
        if (value instanceof List<?> list) {
            return list.stream().map(item -> redactSensitiveValue(item, parentKey)).toList();
        }
        return value;
    }

    private HashMap<String, Object> preserveCurrentSensitiveMap(Map<?, ?> target, Map<?, ?> current) {
        return preserveCurrentSensitiveMap(target, current, null);
    }

    private HashMap<String, Object> preserveCurrentSensitiveMap(Map<?, ?> target, Map<?, ?> current,
            String parentSemanticKey) {
        HashMap<String, Object> result = new HashMap<>();
        if (target == null) {
            return result;
        }
        String structuredSensitiveKey = getStructuredSensitiveKey(target);
        if (structuredSensitiveKey != null) {
            validateStructuredSensitiveDiscriminator(target, current);
        }
        target.forEach((key, value) -> {
            if (key == null) {
                return;
            }
            String keyText = String.valueOf(key);
            String semanticKey = resolveUrlSemanticKey(parentSemanticKey, keyText);
            Object currentValue = getMapValue(current, keyText);
            if (isSensitiveKey(keyText)
                    || (structuredSensitiveKey != null && "value".equalsIgnoreCase(keyText))) {
                result.put(keyText, preserveSensitiveScalar(value, currentValue));
            } else if (value instanceof CharSequence targetUrl
                    && shouldTreatAsUrl(semanticKey, targetUrl.toString())) {
                result.put(keyText, preserveCurrentSensitiveUrl(targetUrl.toString(),
                        currentValue instanceof CharSequence currentUrl ? currentUrl.toString() : null, semanticKey));
            } else {
                result.put(keyText, preserveCurrentSensitiveValue(value, currentValue, semanticKey));
            }
        });
        return result;
    }

    private Object preserveCurrentSensitiveValue(Object target, Object current) {
        return preserveCurrentSensitiveValue(target, current, null);
    }

    private Object preserveCurrentSensitiveValue(Object target, Object current, String parentKey) {
        if (target instanceof CharSequence targetText && shouldTreatAsUrl(parentKey, targetText.toString())) {
            return preserveCurrentSensitiveUrl(targetText.toString(),
                    current instanceof CharSequence currentText ? currentText.toString() : null, parentKey);
        }
        if (target instanceof Map<?, ?> targetMap) {
            return preserveCurrentSensitiveMap(targetMap,
                    current instanceof Map<?, ?> currentMap ? currentMap : null, parentKey);
        }
        if (target instanceof List<?> targetList) {
            List<?> currentList = current instanceof List<?> list ? list : Collections.emptyList();
            return preserveCurrentSensitiveList(targetList, currentList, parentKey);
        }
        return target;
    }

    private List<Object> preserveCurrentSensitiveList(List<?> target, List<?> current, String parentKey) {
        Map<String, List<Object>> targetByIdentity = indexListByStableIdentity(target, parentKey);
        Map<String, List<Object>> currentByIdentity = indexListByStableIdentity(current, parentKey);
        List<Object> result = new ArrayList<>();
        for (Object targetItem : target) {
            List<Object> matchingCurrentItems = stableListIdentities(targetItem, parentKey).stream()
                    .filter(candidate -> targetByIdentity.getOrDefault(candidate, Collections.emptyList()).size() == 1)
                    .filter(candidate -> currentByIdentity.getOrDefault(candidate, Collections.emptyList()).size() == 1)
                    .map(candidate -> currentByIdentity.get(candidate).get(0))
                    .distinct()
                    .toList();
            Object currentItem = matchingCurrentItems.size() == 1 ? matchingCurrentItems.get(0) : null;
            if (currentItem == null && containsSensitiveMaterial(targetItem)) {
                throw new RenException("快照中的敏感列表项缺少唯一稳定标识，无法安全恢复");
            }
            result.add(preserveCurrentSensitiveValue(targetItem, currentItem, parentKey));
        }
        return result;
    }

    private Map<String, List<Object>> indexListByStableIdentity(List<?> values, String parentKey) {
        Map<String, List<Object>> result = new HashMap<>();
        for (Object value : values) {
            for (String identity : stableListIdentities(value, parentKey)) {
                result.computeIfAbsent(identity, ignored -> new ArrayList<>()).add(value);
            }
        }
        return result;
    }

    private List<String> stableListIdentities(Object value, String parentKey) {
        if (value instanceof CharSequence text && shouldTreatAsUrl(parentKey, text.toString())) {
            String identity = normalizeUrlIdentity(text.toString(), parentKey);
            return StringUtils.isBlank(identity) ? Collections.emptyList() : List.of("url:" + identity);
        }
        if (!(value instanceof Map<?, ?> map)) {
            return Collections.emptyList();
        }
        List<String> identities = new ArrayList<>();
        for (String field : List.of("id", "name", "key", "url")) {
            Object identityValue = getMapValue(map, field);
            if (identityValue == null || StringUtils.isBlank(String.valueOf(identityValue))) {
                continue;
            }
            String text = String.valueOf(identityValue).trim();
            if ("url".equals(field)) {
                text = normalizeUrlIdentity(text, resolveUrlSemanticKey(parentKey, field));
            } else if ("name".equals(field) || "key".equals(field)) {
                text = text.toLowerCase(Locale.ROOT);
            }
            identities.add(field + ":" + text);
        }
        if (!map.isEmpty()) {
            identities.add("fingerprint:" + JsonUtils.toJsonString(normalizeMap(map, parentKey)));
        }
        return identities;
    }

    private Object preserveSensitiveScalar(Object target, Object current) {
        if (current != null && !SECRET_PLACEHOLDER.equals(current)) {
            return current;
        }
        throw new RenException("快照敏感值无法与当前配置可靠匹配");
    }

    private Object getMapValue(Map<?, ?> map, String key) {
        if (map == null) {
            return null;
        }
        if (map.containsKey(key)) {
            return map.get(key);
        }
        for (Map.Entry<?, ?> entry : map.entrySet()) {
            if (entry.getKey() != null && key.equalsIgnoreCase(String.valueOf(entry.getKey()))) {
                return entry.getValue();
            }
        }
        return null;
    }

    private List<ContextProviderDTO> preserveCurrentContextProviders(List<ContextProviderDTO> target,
            List<ContextProviderDTO> current) {
        if (target == null) {
            return null;
        }
        List<ContextProviderDTO> currentProviders = nullToEmpty(current);
        Map<String, List<ContextProviderDTO>> targetByIdentity = indexProvidersByIdentity(target);
        Map<String, List<ContextProviderDTO>> currentByIdentity = indexProvidersByIdentity(currentProviders);

        for (ContextProviderDTO targetProvider : target) {
            if (targetProvider == null) {
                continue;
            }
            String identity = normalizeUrlIdentity(targetProvider.getUrl());
            ContextProviderDTO currentProvider = null;
            if (StringUtils.isNotBlank(identity)
                    && targetByIdentity.getOrDefault(identity, Collections.emptyList()).size() == 1
                    && currentByIdentity.getOrDefault(identity, Collections.emptyList()).size() == 1) {
                currentProvider = currentByIdentity.get(identity).get(0);
            } else if (hasSensitiveUrlParts(targetProvider.getUrl())
                    || containsSensitiveMaterial(targetProvider.getHeaders())) {
                throw new RenException("上下文源敏感配置缺少唯一 URL 标识，无法安全恢复");
            }

            if (targetProvider.getUrl() != null) {
                targetProvider.setUrl(preserveCurrentSensitiveUrl(targetProvider.getUrl(),
                        currentProvider == null ? null : currentProvider.getUrl(), "url"));
            }
            targetProvider.setHeaders(preserveCurrentSensitiveMap(targetProvider.getHeaders(),
                    currentProvider == null ? null : currentProvider.getHeaders()));
        }
        return target;
    }

    private Map<String, List<ContextProviderDTO>> indexProvidersByIdentity(List<ContextProviderDTO> providers) {
        Map<String, List<ContextProviderDTO>> result = new HashMap<>();
        for (ContextProviderDTO provider : providers) {
            if (provider == null) {
                continue;
            }
            String identity = normalizeUrlIdentity(provider.getUrl());
            if (StringUtils.isNotBlank(identity)) {
                result.computeIfAbsent(identity, ignored -> new ArrayList<>()).add(provider);
            }
        }
        return result;
    }

    private String getStructuredSensitiveKey(Map<?, ?> map) {
        if (map == null) {
            return null;
        }
        for (String discriminator : List.of("key", "name")) {
            Object value = getMapValue(map, discriminator);
            if (value != null && isSensitiveKey(String.valueOf(value))) {
                return String.valueOf(value);
            }
        }
        return null;
    }

    private void validateStructuredSensitiveDiscriminator(Map<?, ?> target, Map<?, ?> current) {
        List<String> targetIdentities = structuredSensitiveDiscriminatorIdentities(target);
        List<String> currentIdentities = structuredSensitiveDiscriminatorIdentities(current);
        if (targetIdentities.size() != 1 || currentIdentities.size() != 1
                || !Objects.equals(targetIdentities.get(0), currentIdentities.get(0))) {
            throw new RenException("快照结构化敏感值的类型标识无法与当前配置唯一匹配");
        }
    }

    private List<String> structuredSensitiveDiscriminatorIdentities(Map<?, ?> map) {
        if (map == null) {
            return Collections.emptyList();
        }
        List<String> identities = new ArrayList<>();
        for (String discriminator : List.of("key", "name")) {
            Object value = getMapValue(map, discriminator);
            if (value == null || !isSensitiveKey(String.valueOf(value))) {
                continue;
            }
            String identity = String.valueOf(value).toLowerCase(Locale.ROOT).replaceAll("[^a-z0-9]", "");
            if (!identities.contains(identity)) {
                identities.add(identity);
            }
        }
        return identities;
    }

    private boolean containsSensitiveMaterial(Object value) {
        return containsSensitiveMaterial(value, null);
    }

    private boolean containsSensitiveMaterial(Object value, String parentKey) {
        if (SECRET_PLACEHOLDER.equals(value)) {
            return true;
        }
        if (value instanceof Map<?, ?> map) {
            if (getStructuredSensitiveKey(map) != null) {
                return true;
            }
            for (Map.Entry<?, ?> entry : map.entrySet()) {
                if (entry.getKey() == null) {
                    continue;
                }
                String key = String.valueOf(entry.getKey());
                String semanticKey = resolveUrlSemanticKey(parentKey, key);
                if (isSensitiveKey(key)
                        || (entry.getValue() instanceof CharSequence text
                                && shouldTreatAsUrl(semanticKey, text.toString())
                                && hasSensitiveUrlParts(text.toString(), semanticKey))
                        || containsSensitiveMaterial(entry.getValue(), semanticKey)) {
                    return true;
                }
            }
            return false;
        }
        if (value instanceof List<?> list) {
            return list.stream().anyMatch(item -> containsSensitiveMaterial(item, parentKey));
        }
        if (value instanceof CharSequence text && shouldTreatAsUrl(parentKey, text.toString())) {
            return hasSensitiveUrlParts(text.toString(), parentKey);
        }
        return false;
    }

    private boolean isUrlKey(String key) {
        String normalized = StringUtils.defaultString(key).toLowerCase(Locale.ROOT).replaceAll("[^a-z0-9]", "");
        return normalized.endsWith("url")
                || normalized.endsWith("uri")
                || normalized.endsWith("endpoint")
                || normalized.endsWith("webhook");
    }

    private boolean shouldTreatAsUrl(String key, String value) {
        return isUrlKey(key) || isWebhookSemanticKey(key) || looksLikeUrl(value);
    }

    private String resolveUrlSemanticKey(String parentSemanticKey, String childKey) {
        if (isWebhookSemanticKey(childKey)) {
            return childKey;
        }
        if (isWebhookSemanticKey(parentSemanticKey)) {
            // Keep the concrete child name for URL detection while carrying the
            // enclosing webhook capability semantics through arbitrary wrapper maps.
            return StringUtils.isBlank(childKey)
                    ? parentSemanticKey
                    : parentSemanticKey + "." + childKey;
        }
        return childKey;
    }

    private boolean looksLikeUrl(String value) {
        String text = StringUtils.defaultString(value);
        if (text.startsWith("//")) {
            int pathStart = text.indexOf('/', 2);
            String authority = pathStart < 0 ? text.substring(2) : text.substring(2, pathStart);
            return StringUtils.isNotBlank(authority) && authority.chars().noneMatch(Character::isWhitespace);
        }
        int schemeEnd = text.indexOf("://");
        if (schemeEnd <= 0 || !Character.isLetter(text.charAt(0))) {
            return false;
        }
        for (int i = 1; i < schemeEnd; i++) {
            char character = text.charAt(i);
            if (!Character.isLetterOrDigit(character)
                    && character != '+'
                    && character != '-'
                    && character != '.') {
                return false;
            }
        }
        return true;
    }

    private String normalizeUrlForCompare(String value) {
        return normalizeUrlForCompare(value, null);
    }

    private String normalizeUrlForCompare(String value, String semanticKey) {
        return redactSensitiveUrl(value, semanticKey);
    }

    private String redactSensitiveUrl(String value) {
        return redactSensitiveUrl(value, null);
    }

    private String redactSensitiveUrl(String value, String semanticKey) {
        if (value == null) {
            return null;
        }
        SensitiveUrlParts parts = splitSensitiveUrl(value);
        return buildSensitiveUrl(analyzeSensitiveUrlPath(parts.base(), semanticKey).redactedBase(),
                parts.userInfo() == null ? null : SECRET_PLACEHOLDER,
                redactSensitiveUrlParameters(parts.query()),
                redactSensitiveUrlFragment(parts.fragment()));
    }

    private String preserveCurrentSensitiveUrl(String target, String current) {
        return preserveCurrentSensitiveUrl(target, current, null);
    }

    private String preserveCurrentSensitiveUrl(String target, String current, String semanticKey) {
        if (target == null) {
            return null;
        }
        SensitiveUrlParts targetParts = splitSensitiveUrl(target);
        SensitiveUrlParts currentParts = splitSensitiveUrl(StringUtils.defaultString(current));
        SensitivePathAnalysis targetPath = analyzeSensitiveUrlPath(targetParts.base(), semanticKey);
        boolean forceCurrentGenericMarker = targetPath.slots().stream()
                .anyMatch(slot -> slot.identity().startsWith("webhook-suffix:"));
        SensitivePathAnalysis currentPath = analyzeSensitiveUrlPath(currentParts.base(), semanticKey,
                forceCurrentGenericMarker);
        boolean copiesSensitiveComponent = targetParts.userInfo() != null
                || !targetPath.slots().isEmpty()
                || containsSensitiveUrlParameter(targetParts.query())
                || (targetParts.fragment() != null
                        && (!isStructuredUrlComponent(targetParts.fragment())
                                || containsSensitiveUrlParameter(targetParts.fragment())));
        if (copiesSensitiveComponent && !Objects.equals(targetPath.redactedBase(), currentPath.redactedBase())) {
            throw new RenException("快照 URL 敏感信息无法与当前配置的公开地址标识匹配");
        }
        String result = buildSensitiveUrl(preserveSensitiveUrlPath(targetParts.base(), currentParts.base(), semanticKey),
                preserveUrlComponent(targetParts.userInfo(), currentParts.userInfo()),
                preserveSensitiveUrlParameters(targetParts.query(), currentParts.query()),
                preserveSensitiveUrlFragment(targetParts.fragment(), currentParts.fragment()));
        if (result.contains(SECRET_PLACEHOLDER)) {
            throw new RenException("快照 URL 中仍包含脱敏占位符，无法安全恢复");
        }
        return result;
    }

    private String preserveUrlComponent(String target, String current) {
        if (target == null) {
            return null;
        }
        if (current == null || current.contains(SECRET_PLACEHOLDER)) {
            throw new RenException("快照 URL 中的敏感信息无法与当前配置可靠匹配");
        }
        return current;
    }

    private String redactSensitiveUrlParameters(String value) {
        if (value == null) {
            return null;
        }
        return buildUrlParameters(parseUrlParameters(value).stream()
                .map(parameter -> isSensitiveUrlParameter(parameter)
                        ? new UrlParameter(parameter.rawKey(), SECRET_PLACEHOLDER, parameter.hasEquals())
                        : parameter)
                .toList());
    }

    private String redactSensitiveUrlFragment(String value) {
        if (value == null) {
            return null;
        }
        return isStructuredUrlComponent(value)
                ? redactSensitiveUrlParameters(value)
                : SECRET_PLACEHOLDER;
    }

    private String preserveSensitiveUrlParameters(String target, String current) {
        if (target == null) {
            return null;
        }
        List<UrlParameter> targetParameters = parseUrlParameters(target);
        List<UrlParameter> currentParameters = parseUrlParameters(StringUtils.defaultString(current));
        Map<String, List<UrlParameter>> targetSensitiveParameters = indexSensitiveUrlParameters(targetParameters);
        Map<String, List<UrlParameter>> currentSensitiveParameters = indexSensitiveUrlParameters(currentParameters);
        List<UrlParameter> result = new ArrayList<>();

        for (UrlParameter targetParameter : targetParameters) {
            if (!isSensitiveUrlParameter(targetParameter)) {
                result.add(targetParameter);
                continue;
            }
            String identity = normalizeUrlParameterName(targetParameter.rawKey());
            List<UrlParameter> matchingTargets = targetSensitiveParameters.getOrDefault(identity,
                    Collections.emptyList());
            List<UrlParameter> matchingCurrent = currentSensitiveParameters.getOrDefault(identity,
                    Collections.emptyList());
            if (matchingTargets.size() != 1 || matchingCurrent.size() != 1) {
                throw new RenException("快照 URL 中的敏感参数无法与当前配置唯一匹配");
            }
            UrlParameter currentParameter = matchingCurrent.get(0);
            if (currentParameter.rawValue().contains(SECRET_PLACEHOLDER)) {
                throw new RenException("快照 URL 中的敏感信息无法与当前配置可靠匹配");
            }
            result.add(new UrlParameter(targetParameter.rawKey(), currentParameter.rawValue(),
                    currentParameter.hasEquals()));
        }
        return buildUrlParameters(result);
    }

    private String preserveSensitiveUrlFragment(String target, String current) {
        if (target == null) {
            return null;
        }
        return isStructuredUrlComponent(target)
                ? preserveSensitiveUrlParameters(target, current)
                : preserveUrlComponent(target, current);
    }

    private Map<String, List<UrlParameter>> indexSensitiveUrlParameters(List<UrlParameter> parameters) {
        Map<String, List<UrlParameter>> result = new HashMap<>();
        for (UrlParameter parameter : parameters) {
            if (isSensitiveUrlParameter(parameter)) {
                result.computeIfAbsent(normalizeUrlParameterName(parameter.rawKey()), ignored -> new ArrayList<>())
                        .add(parameter);
            }
        }
        return result;
    }

    private List<UrlParameter> parseUrlParameters(String value) {
        List<UrlParameter> result = new ArrayList<>();
        for (String part : StringUtils.defaultString(value).split("&", -1)) {
            int equalsIndex = part.indexOf('=');
            if (equalsIndex < 0) {
                result.add(new UrlParameter(part, "", false));
            } else {
                result.add(new UrlParameter(part.substring(0, equalsIndex), part.substring(equalsIndex + 1), true));
            }
        }
        return result;
    }

    private String buildUrlParameters(List<UrlParameter> parameters) {
        return parameters.stream()
                .map(parameter -> parameter.rawKey()
                        + (parameter.hasEquals() ? "=" + parameter.rawValue() : ""))
                .collect(Collectors.joining("&"));
    }

    private boolean isSensitiveUrlParameter(UrlParameter parameter) {
        String decodedName = decodeUrlParameterName(parameter.rawKey());
        String normalized = decodedName.toLowerCase(Locale.ROOT).replaceAll("[^a-z0-9]", "");
        return isSensitiveKey(decodedName)
                || normalized.equals("key")
                || normalized.equals("sig")
                || normalized.equals("signature")
                || normalized.equals("xamzsignature")
                || normalized.equals("xgoogsignature")
                || normalized.equals("sas");
    }

    private String normalizeUrlParameterName(String value) {
        return decodeUrlParameterName(value).toLowerCase(Locale.ROOT).replaceAll("[^a-z0-9]", "");
    }

    private String decodeUrlParameterName(String value) {
        try {
            return URLDecoder.decode(StringUtils.defaultString(value), StandardCharsets.UTF_8);
        } catch (IllegalArgumentException ignored) {
            return StringUtils.defaultString(value);
        }
    }

    private boolean isStructuredUrlComponent(String value) {
        return value != null && (value.contains("=") || value.contains("&"));
    }

    private boolean hasSensitiveUrlParts(String value) {
        return hasSensitiveUrlParts(value, null);
    }

    private boolean hasSensitiveUrlParts(String value, String semanticKey) {
        if (StringUtils.isBlank(value)) {
            return false;
        }
        SensitiveUrlParts parts = splitSensitiveUrl(value);
        return parts.userInfo() != null
                || !analyzeSensitiveUrlPath(parts.base(), semanticKey).slots().isEmpty()
                || containsSensitiveUrlParameter(parts.query())
                || (parts.fragment() != null
                        && (!isStructuredUrlComponent(parts.fragment())
                                || containsSensitiveUrlParameter(parts.fragment())));
    }

    private boolean containsSensitiveUrlParameter(String value) {
        return value != null && parseUrlParameters(value).stream().anyMatch(this::isSensitiveUrlParameter);
    }

    private String normalizeUrlIdentity(String value) {
        return normalizeUrlIdentity(value, null);
    }

    private String normalizeUrlIdentity(String value, String semanticKey) {
        if (StringUtils.isBlank(value)) {
            return "";
        }
        SensitiveUrlParts parts = splitSensitiveUrl(value);
        return analyzeSensitiveUrlPath(parts.base(), semanticKey).redactedBase();
    }

    private String preserveSensitiveUrlPath(String targetBase, String currentBase, String semanticKey) {
        SensitivePathAnalysis target = analyzeSensitiveUrlPath(targetBase, semanticKey);
        if (target.slots().isEmpty()) {
            return targetBase;
        }
        boolean forceCurrentGenericMarker = target.slots().stream()
                .anyMatch(slot -> slot.identity().startsWith("webhook-suffix:"));
        SensitivePathAnalysis current = analyzeSensitiveUrlPath(currentBase, semanticKey, forceCurrentGenericMarker);
        if (!Objects.equals(target.redactedBase(), current.redactedBase())
                || target.slots().size() != current.slots().size()) {
            throw new RenException("快照 URL 路径敏感信息无法与当前配置的公开标识唯一匹配");
        }

        Map<String, List<SensitivePathSlot>> currentSlots = current.slots().stream()
                .collect(Collectors.groupingBy(SensitivePathSlot::identity));
        Map<String, SensitivePathSlot> replacements = new HashMap<>();
        for (SensitivePathSlot targetSlot : target.slots()) {
            List<SensitivePathSlot> matches = currentSlots.getOrDefault(targetSlot.identity(), Collections.emptyList());
            if (matches.size() != 1 || matches.get(0).secretSegments().isEmpty()
                    || matches.get(0).secretSegments().stream()
                            .anyMatch(secret -> StringUtils.isBlank(secret) || secret.contains(SECRET_PLACEHOLDER))) {
                throw new RenException("快照 URL 路径敏感信息无法与当前配置可靠匹配");
            }
            if (replacements.put(targetSlot.identity(), matches.get(0)) != null) {
                throw new RenException("快照 URL 路径敏感信息存在歧义，无法安全恢复");
            }
        }
        return rebuildSensitivePath(target, replacements);
    }

    private SensitivePathAnalysis analyzeSensitiveUrlPath(String base, String semanticKey) {
        return analyzeSensitiveUrlPath(base, semanticKey, false);
    }

    private SensitivePathAnalysis analyzeSensitiveUrlPath(String base, String semanticKey,
            boolean forceGenericMarker) {
        UrlPathParts pathParts = splitUrlPath(base);
        if (pathParts == null || pathParts.segments().isEmpty()) {
            return new SensitivePathAnalysis(base, base, Collections.emptyList());
        }
        List<String> segments = pathParts.segments();
        List<SensitivePathSlot> slots = new ArrayList<>();
        List<Integer> claimedMarkers = new ArrayList<>();

        if (isSlackHooksHost(pathParts.host())) {
            for (int i = 0; i + 3 < segments.size(); i++) {
                if ("services".equalsIgnoreCase(segments.get(i))
                        && allPathSegmentsPresent(segments, i + 1, i + 4)) {
                    addSensitivePathSlot(slots, new SensitivePathSlot("slack:" + i, i + 3, i + 4, "",
                            List.of(segments.get(i + 3))));
                }
            }
        }

        if (isDiscordHost(pathParts.host())) {
            for (int i = 0; i + 2 < segments.size(); i++) {
                if ("webhooks".equalsIgnoreCase(segments.get(i))
                        && isDiscordWebhookPrefix(segments, i)
                        && allPathSegmentsPresent(segments, i + 1, i + 3)) {
                    addSensitivePathSlot(slots, new SensitivePathSlot("discord:" + i, i + 2, i + 3, "",
                            List.of(segments.get(i + 2))));
                    claimedMarkers.add(i);
                }
            }
        }

        if (isTelegramHost(pathParts.host())) {
            for (int i = 0; i < segments.size(); i++) {
                String segment = segments.get(i);
                int colon = segment.indexOf(':');
                if (segment.regionMatches(true, 0, "bot", 0, 3)
                        && colon > 3 && colon < segment.length() - 1) {
                    String publicPrefix = segment.substring(0, colon + 1);
                    addSensitivePathSlot(slots, new SensitivePathSlot("telegram:" + i + ":" + publicPrefix,
                            i, i + 1, publicPrefix, List.of(segment.substring(colon + 1))));
                }
            }
        }

        for (int i = 0; i < segments.size(); i++) {
            if (!isWebhookPathMarker(segments.get(i)) || claimedMarkers.contains(i) || i + 1 >= segments.size()) {
                continue;
            }
            int suffixEnd = segments.size();
            while (suffixEnd > i + 1 && StringUtils.isBlank(segments.get(suffixEnd - 1))) {
                suffixEnd--;
            }
            List<String> capabilitySuffix = new ArrayList<>(segments.subList(i + 1, suffixEnd));
            if (capabilitySuffix.isEmpty()) {
                continue;
            }
            if (capabilitySuffix.stream().anyMatch(StringUtils::isBlank)) {
                continue;
            }
            if (!forceGenericMarker
                    && !isHighConfidenceWebhookCapability(pathParts, semanticKey, capabilitySuffix)) {
                continue;
            }
            addSensitivePathSlot(slots, new SensitivePathSlot("webhook-suffix:" + i, i + 1, suffixEnd, "",
                    capabilitySuffix));
            break;
        }

        if (slots.isEmpty() && isWebhookSemanticKey(semanticKey)) {
            int lastSegment = segments.size() - 1;
            while (lastSegment >= 0 && StringUtils.isBlank(segments.get(lastSegment))) {
                lastSegment--;
            }
            if (lastSegment >= 0 && StringUtils.isNotBlank(segments.get(lastSegment))) {
                addSensitivePathSlot(slots, new SensitivePathSlot("webhook-key:" + lastSegment,
                        lastSegment, lastSegment + 1, "", List.of(segments.get(lastSegment))));
            }
        }

        if (slots.isEmpty()) {
            return new SensitivePathAnalysis(base, base, Collections.emptyList());
        }
        SensitivePathAnalysis analysis = new SensitivePathAnalysis(base, null, slots);
        return new SensitivePathAnalysis(base, rebuildSensitivePath(analysis, Collections.emptyMap()), slots);
    }

    private String rebuildSensitivePath(SensitivePathAnalysis analysis,
            Map<String, SensitivePathSlot> replacements) {
        UrlPathParts pathParts = splitUrlPath(analysis.originalBase());
        if (pathParts == null) {
            return analysis.originalBase();
        }
        Map<Integer, SensitivePathSlot> slotsByStart = analysis.slots().stream()
                .collect(Collectors.toMap(SensitivePathSlot::startIndex, Function.identity(), (left, right) -> left));
        List<String> result = new ArrayList<>();
        for (int i = 0; i < pathParts.segments().size();) {
            SensitivePathSlot slot = slotsByStart.get(i);
            if (slot == null) {
                result.add(pathParts.segments().get(i));
                i++;
                continue;
            }
            SensitivePathSlot replacement = replacements.get(slot.identity());
            if (replacement == null) {
                result.add(slot.publicPrefix() + SECRET_PLACEHOLDER);
            } else if (StringUtils.isNotEmpty(slot.publicPrefix())) {
                result.add(slot.publicPrefix() + replacement.secretSegments().get(0));
            } else {
                result.addAll(replacement.secretSegments());
            }
            i = slot.endIndex();
        }
        return pathParts.prefix() + String.join("/", result);
    }

    private UrlPathParts splitUrlPath(String base) {
        String value = StringUtils.defaultString(base);
        int schemeIndex = value.indexOf("://");
        if (schemeIndex < 0 && !value.startsWith("/")) {
            if (StringUtils.isBlank(value) || value.chars().anyMatch(Character::isWhitespace)) {
                return null;
            }
            return new UrlPathParts("",
                    new ArrayList<>(List.of(value.split("/", -1))), "");
        }
        if (schemeIndex < 0 && !value.startsWith("//")) {
            return new UrlPathParts("",
                    new ArrayList<>(List.of(value.split("/", -1))), "");
        }
        int authorityStart = schemeIndex < 0 ? 2 : schemeIndex + 3;
        int pathStart = value.indexOf('/', authorityStart);
        String authority = pathStart < 0 ? value.substring(authorityStart) : value.substring(authorityStart, pathStart);
        String host = normalizeAuthorityHost(authority);
        if (pathStart < 0) {
            return new UrlPathParts(value, Collections.emptyList(), host);
        }
        return new UrlPathParts(value.substring(0, pathStart),
                new ArrayList<>(List.of(value.substring(pathStart).split("/", -1))), host);
    }

    private String normalizeAuthorityHost(String authority) {
        String value = StringUtils.defaultString(authority).toLowerCase(Locale.ROOT);
        if (value.startsWith("[")) {
            int closingBracket = value.indexOf(']');
            return closingBracket < 0 ? value : value.substring(0, closingBracket + 1);
        }
        int portSeparator = value.lastIndexOf(':');
        return portSeparator < 0 ? value : value.substring(0, portSeparator);
    }

    private boolean isSlackHooksHost(String host) {
        return "hooks.slack.com".equals(host) || "hooks.slack-gov.com".equals(host);
    }

    private boolean isDiscordHost(String host) {
        return "discord.com".equals(host) || host.endsWith(".discord.com")
                || "discordapp.com".equals(host) || host.endsWith(".discordapp.com");
    }

    private boolean isTelegramHost(String host) {
        return "api.telegram.org".equals(host);
    }

    private boolean isDiscordWebhookPrefix(List<String> segments, int markerIndex) {
        if (markerIndex >= 1 && "api".equalsIgnoreCase(segments.get(markerIndex - 1))) {
            return true;
        }
        return markerIndex >= 2
                && "api".equalsIgnoreCase(segments.get(markerIndex - 2))
                && isVersionPathSegment(segments.get(markerIndex - 1));
    }

    private boolean isVersionPathSegment(String value) {
        String normalized = StringUtils.defaultString(value).toLowerCase(Locale.ROOT);
        return normalized.length() > 1 && normalized.charAt(0) == 'v'
                && normalized.substring(1).chars().allMatch(Character::isDigit);
    }

    private boolean isWebhookPathMarker(String value) {
        String normalized = StringUtils.defaultString(value).toLowerCase(Locale.ROOT);
        return normalized.equals("webhook") || normalized.equals("webhooks")
                || normalized.equals("hook") || normalized.equals("hooks");
    }

    private boolean isHighConfidenceWebhookCapability(UrlPathParts pathParts, String semanticKey,
            List<String> capabilitySuffix) {
        return isWebhookSemanticKey(semanticKey)
                || hasWebhookHostLabel(pathParts.host())
                || isSlackHooksHost(pathParts.host())
                || isDiscordHost(pathParts.host())
                || isTelegramHost(pathParts.host())
                || capabilitySuffix.stream().anyMatch(this::looksLikeCapabilitySecret);
    }

    private boolean hasWebhookHostLabel(String host) {
        return List.of(StringUtils.defaultString(host).split("\\.")).stream()
                .anyMatch(this::isWebhookPathMarker);
    }

    private boolean looksLikeCapabilitySecret(String value) {
        String text = StringUtils.defaultString(value);
        String normalized = text.toLowerCase(Locale.ROOT).replaceAll("[^a-z0-9]", "");
        if (normalized.contains("secret")
                || normalized.contains("token")
                || normalized.contains("capability")
                || normalized.contains("credential")
                || normalized.contains("signature")
                || normalized.contains("apikey")
                || normalized.contains("accesskey")
                || normalized.contains("authkey")) {
            return true;
        }
        if (text.length() < 20) {
            return false;
        }
        boolean hasLetter = text.chars().anyMatch(Character::isLetter);
        boolean hasDigit = text.chars().anyMatch(Character::isDigit);
        boolean hasSymbol = text.chars().anyMatch(character -> !Character.isLetterOrDigit(character));
        long distinctCharacters = text.chars().distinct().count();
        return distinctCharacters >= 10
                && ((hasLetter && hasDigit) || (hasLetter && hasSymbol) || (hasDigit && hasSymbol));
    }

    private boolean isWebhookSemanticKey(String value) {
        String normalized = StringUtils.defaultString(value).toLowerCase(Locale.ROOT).replaceAll("[^a-z0-9]", "");
        return normalized.contains("webhook") || normalized.equals("hook") || normalized.equals("hooks")
                || normalized.endsWith("hook") || normalized.endsWith("hooks");
    }

    private boolean allPathSegmentsPresent(List<String> segments, int fromInclusive, int toExclusive) {
        return segments.subList(fromInclusive, toExclusive).stream().noneMatch(StringUtils::isBlank);
    }

    private void addSensitivePathSlot(List<SensitivePathSlot> slots, SensitivePathSlot candidate) {
        boolean overlaps = slots.stream().anyMatch(slot -> candidate.startIndex() < slot.endIndex()
                && slot.startIndex() < candidate.endIndex());
        if (!overlaps) {
            slots.add(candidate);
        }
    }

    private SensitiveUrlParts splitSensitiveUrl(String value) {
        String remaining = StringUtils.defaultString(value);
        String fragment = null;
        int fragmentIndex = remaining.indexOf('#');
        if (fragmentIndex >= 0) {
            fragment = remaining.substring(fragmentIndex + 1);
            remaining = remaining.substring(0, fragmentIndex);
        }
        String query = null;
        int queryIndex = remaining.indexOf('?');
        if (queryIndex >= 0) {
            query = remaining.substring(queryIndex + 1);
            remaining = remaining.substring(0, queryIndex);
        }

        String userInfo = null;
        int schemeIndex = remaining.indexOf("://");
        int authorityStart = schemeIndex >= 0
                ? schemeIndex + 3
                : remaining.startsWith("//") ? 2 : -1;
        if (authorityStart >= 0) {
            int pathStart = remaining.indexOf('/', authorityStart);
            if (pathStart < 0) {
                pathStart = remaining.length();
            }
            String authority = remaining.substring(authorityStart, pathStart);
            int userInfoEnd = authority.lastIndexOf('@');
            if (userInfoEnd >= 0) {
                userInfo = authority.substring(0, userInfoEnd);
                remaining = remaining.substring(0, authorityStart)
                        + authority.substring(userInfoEnd + 1)
                        + remaining.substring(pathStart);
            }
        }
        return new SensitiveUrlParts(remaining, userInfo, query, fragment);
    }

    private String buildSensitiveUrl(String base, String userInfo, String query, String fragment) {
        String result = StringUtils.defaultString(base);
        if (userInfo != null) {
            int schemeIndex = result.indexOf("://");
            int authorityStart = schemeIndex >= 0
                    ? schemeIndex + 3
                    : result.startsWith("//") ? 2 : -1;
            if (authorityStart < 0) {
                throw new RenException("带用户凭据的 URL 格式无效，无法安全恢复");
            }
            result = result.substring(0, authorityStart) + userInfo + "@" + result.substring(authorityStart);
        }
        if (query != null) {
            result += "?" + query;
        }
        if (fragment != null) {
            result += "#" + fragment;
        }
        return result;
    }

    private record SensitiveUrlParts(String base, String userInfo, String query, String fragment) {
    }

    private record UrlPathParts(String prefix, List<String> segments, String host) {
    }

    private record SensitivePathAnalysis(String originalBase, String redactedBase,
            List<SensitivePathSlot> slots) {
    }

    private record SensitivePathSlot(String identity, int startIndex, int endIndex,
            String publicPrefix, List<String> secretSegments) {
    }

    private record UrlParameter(String rawKey, String rawValue, boolean hasEquals) {
    }

    private boolean isSensitiveKey(String key) {
        String normalized = StringUtils.defaultString(key).toLowerCase(Locale.ROOT).replaceAll("[^a-z0-9]", "");
        return normalized.equals("authorization")
                || normalized.contains("authorization")
                || normalized.contains("authentication")
                || normalized.equals("auth")
                || normalized.endsWith("auth")
                || normalized.equals("cookie")
                || normalized.equals("cookie2")
                || normalized.equals("setcookie")
                || normalized.equals("setcookie2")
                || normalized.endsWith("cookie")
                || normalized.equals("session")
                || normalized.endsWith("session")
                || normalized.contains("sessionid")
                || normalized.contains("sessionkey")
                || normalized.contains("sessiontoken")
                || normalized.contains("sessioncookie")
                || normalized.endsWith("sessid")
                || normalized.equals("token")
                || normalized.endsWith("token")
                || normalized.contains("apikey")
                || normalized.contains("appkey")
                || normalized.contains("accesskey")
                || normalized.contains("subscriptionkey")
                || normalized.contains("privatekey")
                || normalized.contains("password")
                || normalized.contains("passwd")
                || normalized.contains("secret")
                || normalized.contains("credential");
    }

    private <T> List<T> nullToEmpty(List<T> list) {
        return list == null ? Collections.emptyList() : list;
    }
}
