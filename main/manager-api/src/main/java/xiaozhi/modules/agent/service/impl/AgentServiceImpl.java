package xiaozhi.modules.agent.service.impl;

import java.util.ArrayList;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.function.Function;
import java.util.stream.Collectors;

import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.repository.IRepository;

import cn.hutool.core.collection.CollUtil;
import lombok.AllArgsConstructor;
import xiaozhi.common.constant.Constant;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.page.PageData;
import xiaozhi.common.redis.RedisKeys;
import xiaozhi.common.redis.RedisUtils;
import xiaozhi.common.service.impl.BaseServiceImpl;
import xiaozhi.common.user.UserDetail;
import xiaozhi.common.utils.ConvertUtils;
import xiaozhi.common.utils.JsonUtils;
import xiaozhi.modules.agent.dao.AgentDao;
import xiaozhi.modules.agent.dao.AgentTagDao;
import xiaozhi.modules.agent.dto.AgentCreateDTO;
import xiaozhi.modules.agent.dto.AgentDTO;
import xiaozhi.modules.agent.dto.AgentMemoryDTO;
import xiaozhi.modules.agent.dto.AgentTagDTO;
import xiaozhi.modules.agent.dto.AgentUpdateDTO;
import xiaozhi.modules.agent.entity.AgentContextProviderEntity;
import xiaozhi.modules.agent.entity.AgentEntity;
import xiaozhi.modules.agent.entity.AgentPluginMapping;
import xiaozhi.modules.agent.entity.AgentTagEntity;
import xiaozhi.modules.agent.entity.AgentTemplateEntity;
import xiaozhi.modules.agent.service.AgentChatHistoryService;
import xiaozhi.modules.agent.service.AgentContextProviderService;
import xiaozhi.modules.agent.service.AgentPluginMappingService;
import xiaozhi.modules.agent.service.AgentService;
import xiaozhi.modules.agent.service.AgentSnapshotService;
import xiaozhi.modules.agent.service.AgentTagService;
import xiaozhi.modules.agent.service.AgentTemplateService;
import xiaozhi.modules.agent.vo.AgentInfoVO;
import xiaozhi.modules.correctword.service.CorrectWordFileService;
import xiaozhi.modules.device.entity.DeviceEntity;
import xiaozhi.modules.device.service.DeviceService;
import xiaozhi.modules.model.dto.ModelProviderDTO;
import xiaozhi.modules.model.dto.VoiceDTO;
import xiaozhi.modules.model.entity.ModelConfigEntity;
import xiaozhi.modules.model.service.ModelConfigService;
import xiaozhi.modules.model.service.ModelProviderService;
import xiaozhi.modules.security.user.SecurityUser;
import xiaozhi.modules.sys.enums.SuperAdminEnum;
import xiaozhi.modules.timbre.service.TimbreService;

@Service
@AllArgsConstructor
public class AgentServiceImpl extends BaseServiceImpl<AgentDao, AgentEntity> implements AgentService {
    private final AgentDao agentDao;
    private final AgentTagDao agentTagDao;
    private final TimbreService timbreModelService;
    private final ModelConfigService modelConfigService;
    private final RedisUtils redisUtils;
    private final DeviceService deviceService;
    private final AgentPluginMappingService agentPluginMappingService;
    private final AgentChatHistoryService agentChatHistoryService;
    private final AgentTemplateService agentTemplateService;
    private final ModelProviderService modelProviderService;
    private final AgentContextProviderService agentContextProviderService;
    private final AgentTagService agentTagService;
    private final CorrectWordFileService correctWordFileService;
    private final AgentSnapshotService agentSnapshotService;

    @Override
    public PageData<AgentEntity> adminAgentList(Map<String, Object> params) {
        IPage<AgentEntity> page = agentDao.selectPage(
                getPage(params, "agent_name", true),
                new QueryWrapper<>());
        return new PageData<>(page.getRecords(), page.getTotal());
    }

    @Override
    public AgentInfoVO getAgentById(String id) {
        AgentInfoVO agent = agentDao.selectAgentInfoById(id);

        if (agent == null) {
            throw new RenException(ErrorCode.AGENT_NOT_FOUND);
        }
        requireCurrentUserPermissionIfPresent(agent);

        if (agent.getMemModelId() != null && agent.getMemModelId().equals(Constant.MEMORY_NO_MEM)) {
            agent.setChatHistoryConf(Constant.ChatHistoryConfEnum.IGNORE.getCode());
        }
        if (agent.getChatHistoryConf() == null) {
            agent.setChatHistoryConf(Constant.ChatHistoryConfEnum.RECORD_TEXT_AUDIO.getCode());
        }

        // Query context source configuration
        AgentContextProviderEntity contextProviderEntity = agentContextProviderService.getByAgentId(id);
        if (contextProviderEntity != null) {
            agent.setContextProviders(contextProviderEntity.getContextProviders());
        }

        // Query replacement word file ID list
        List<String> correctWordFileIds = correctWordFileService.getAgentCorrectWordFileIds(id);
        agent.setCorrectWordFileIds(correctWordFileIds);
        agent.setCurrentVersionNo(agentSnapshotService.getCurrentVersionNo(id));

        // No additional plugin list query needed; already retrieved via SQL
        return agent;
    }

    @Override
    public AgentInfoVO getAgentById(String id, Long userId) {
        AgentInfoVO agent = getAgentById(id);
        requireAgentPermission(agent, userId);
        return agent;
    }

    private AgentEntity getAgentEntityOrThrow(String agentId) {
        AgentEntity agent = agentDao.selectById(agentId);
        if (agent == null) {
            throw new RenException(ErrorCode.AGENT_NOT_FOUND);
        }
        return agent;
    }

    private boolean isCurrentUserSuperAdmin() {
        UserDetail user = SecurityUser.getUser();
        return user != null && Integer.valueOf(SuperAdminEnum.YES.value()).equals(user.getSuperAdmin());
    }

    private void requireCurrentUserPermissionIfPresent(AgentEntity agent) {
        Long userId = SecurityUser.getUserId();
        if (userId != null) {
            requireAgentPermission(agent, userId);
        }
    }

    private boolean hasAgentPermission(AgentEntity agent, Long userId) {
        if (agent == null) {
            return false;
        }
        if (isCurrentUserSuperAdmin()) {
            return true;
        }
        return userId != null && userId.equals(agent.getUserId());
    }

    private void requireAgentPermission(AgentEntity agent, Long userId) {
        if (!hasAgentPermission(agent, userId)) {
            throw new RenException(ErrorCode.NO_PERMISSION);
        }
    }

    private boolean hasDevicePermission(DeviceEntity device, Long userId) {
        if (device == null) {
            return false;
        }
        if (isCurrentUserSuperAdmin()) {
            return true;
        }
        return userId != null && userId.equals(device.getUserId());
    }

    private void requireDevicePermission(DeviceEntity device, Long userId) {
        if (!hasDevicePermission(device, userId)) {
            throw new RenException(ErrorCode.NO_PERMISSION);
        }
    }

    @Override
    public boolean insert(AgentEntity entity) {
        // If ID is empty, generate a UUID as ID
        if (entity.getId() == null || entity.getId().trim().isEmpty()) {
            entity.setId(UUID.randomUUID().toString().replace("-", ""));
        }

        // If the Agent code is empty, auto-generate a code with a prefix
        if (entity.getAgentCode() == null || entity.getAgentCode().trim().isEmpty()) {
            entity.setAgentCode("AGT_" + System.currentTimeMillis());
        }

        // If sort field is empty, set default value to 0
        if (entity.getSort() == null) {
            entity.setSort(0);
        }

        return super.insert(entity);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deleteAgentByUserId(Long userId) {
        List<AgentEntity> agents = baseDao.selectList(new QueryWrapper<AgentEntity>()
                .select("id")
                .eq("user_id", userId));
        for (AgentEntity agent : agents) {
            deleteAgent(agent.getId());
        }
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deleteAgent(String agentId) {
        if (agentDao.selectByIdForUpdate(agentId) == null) {
            return;
        }
        deviceService.deleteByAgentId(agentId);
        agentChatHistoryService.deleteByAgentId(agentId, true, true);
        agentPluginMappingService.deleteByAgentId(agentId);
        agentContextProviderService.deleteByAgentId(agentId);
        correctWordFileService.deleteMappingsByAgentId(agentId);
        agentTagService.deleteAgentTags(agentId);
        agentSnapshotService.deleteByAgentId(agentId);
        deleteById(agentId);
    }

    @Override
    public List<AgentDTO> getUserAgents(Long userId, String keyword, String searchType) {
        QueryWrapper<AgentEntity> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("user_id", userId).orderByDesc("created_at");

        if (StringUtils.isNotBlank(keyword)) {
            queryWrapper.and(w -> {
                // Search by name
                w.like("agent_name", keyword);

                // Search by MAC address: query device first, then retrieve the corresponding Agent ID
                List<DeviceEntity> devices = Optional
                        .ofNullable(deviceService.searchDevicesByMacAddress(keyword, userId))
                        .orElseGet(ArrayList::new);
                List<String> agentIds = devices.stream()
                        .map(DeviceEntity::getAgentId)
                        .distinct()
                        .collect(Collectors.toList());
                if (CollUtil.isNotEmpty(agentIds)) {
                    w.or().in("id", agentIds);
                }

                // Search by tag name
                List<String> tagAgentIds = agentTagService.getAgentIdsByTagName(keyword);
                if (CollUtil.isNotEmpty(tagAgentIds)) {
                    w.or().in("id", tagAgentIds);
                }
            });
        }

        List<AgentEntity> agentEntities = baseDao.selectList(queryWrapper);
        return agentEntities.stream().map(this::buildAgentDTO).collect(Collectors.toList());
    }

    /**
     * Convert AgentEntity to AgentDTO
     */
    private AgentDTO buildAgentDTO(AgentEntity agent) {
        AgentDTO dto = new AgentDTO();
        dto.setId(agent.getId());
        dto.setAgentName(agent.getAgentName());
        dto.setSystemPrompt(agent.getSystemPrompt());

        // Get TTS model name
        dto.setTtsModelName(modelConfigService.getModelNameById(agent.getTtsModelId()));

        // Get LLM model name
        dto.setLlmModelName(modelConfigService.getModelNameById(agent.getLlmModelId()));

        // Get VLLM model name
        dto.setVllmModelName(modelConfigService.getModelNameById(agent.getVllmModelId()));

        // Get memory model name
        dto.setMemModelId(agent.getMemModelId());

        // Get TTS voice name
        dto.setTtsVoiceName(timbreModelService.getTimbreNameById(agent.getTtsVoiceId()));

        // Get the Agent's recent last connection duration
        dto.setLastConnectedAt(deviceService.getLatestLastConnectionTime(agent.getId()));

        // Get device count
        dto.setDeviceCount(getDeviceCountByAgentId(agent.getId()));

        // Get tag list
        List<AgentTagEntity> tags = agentTagDao.selectByAgentId(agent.getId());
        if (CollUtil.isNotEmpty(tags)) {
            dto.setTags(tags.stream().map(this::convertTagToDTO).collect(Collectors.toList()));
        }

        return dto;
    }

    private AgentTagDTO convertTagToDTO(AgentTagEntity entity) {
        AgentTagDTO dto = new AgentTagDTO();
        dto.setId(entity.getId());
        dto.setTagName(entity.getTagName());
        return dto;
    }

    @Override
    public Integer getDeviceCountByAgentId(String agentId) {
        if (StringUtils.isBlank(agentId)) {
            return 0;
        }

        // Fetch from Redis first
        Integer cachedCount = (Integer) redisUtils.get(RedisKeys.getAgentDeviceCountById(agentId));
        if (cachedCount != null) {
            return cachedCount;
        }

        // If not found in Redis, query from the database
        Integer deviceCount = agentDao.getDeviceCountByAgentId(agentId);

        // Store result in Redis
        if (deviceCount != null) {
            redisUtils.set(RedisKeys.getAgentDeviceCountById(agentId), deviceCount, 60);
        }

        return deviceCount != null ? deviceCount : 0;
    }

    @Override
    public AgentEntity getDefaultAgentByMacAddress(String macAddress) {
        if (StringUtils.isEmpty(macAddress)) {
            return null;
        }
        return agentDao.getDefaultAgentByMacAddress(macAddress);
    }

    @Override
    public boolean checkAgentPermission(String agentId, Long userId) {
        AgentEntity agent = agentDao.selectById(agentId);
        return hasAgentPermission(agent, userId);
    }

    // Update agent info by ID
    @Override
    @Transactional(rollbackFor = Exception.class)
    public void updateAgentById(String agentId, AgentUpdateDTO dto) {
        updateAgentById(agentId, dto, true);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void updateAgentById(String agentId, AgentUpdateDTO dto, Long userId) {
        updateAgentById(agentId, dto, userId, true);
    }

    // Update agent info by ID
    @Override
    @Transactional(rollbackFor = Exception.class)
    public void updateAgentById(String agentId, AgentUpdateDTO dto, boolean createSnapshot) {
        updateAgentById(agentId, dto, null, createSnapshot);
    }

    private void updateAgentById(String agentId, AgentUpdateDTO dto, Long userId, boolean createSnapshot) {
        AgentEntity lockedAgent = agentDao.selectByIdForUpdate(agentId);
        if (lockedAgent == null) {
            throw new RenException(ErrorCode.AGENT_NOT_FOUND);
        }
        if (userId == null) {
            requireCurrentUserPermissionIfPresent(lockedAgent);
        } else {
            requireAgentPermission(lockedAgent, userId);
        }

        // Query existing entities and associated configs after locking
        AgentEntity existingEntity = this.getAgentById(agentId);
        if (createSnapshot) {
            int currentVersionNo = agentSnapshotService.getCurrentVersionNo(agentId);
            agentSnapshotService.createSnapshot(agentId, currentVersionNo == 0 ? "initial" : "current");
        }

        // Update only provided non-empty fields
        if (dto.getAgentName() != null) {
            existingEntity.setAgentName(dto.getAgentName());
        }
        if (dto.getAgentCode() != null) {
            existingEntity.setAgentCode(dto.getAgentCode());
        }
        if (dto.getAsrModelId() != null) {
            existingEntity.setAsrModelId(dto.getAsrModelId());
        }
        if (dto.getVadModelId() != null) {
            existingEntity.setVadModelId(dto.getVadModelId());
        }
        if (dto.getLlmModelId() != null) {
            existingEntity.setLlmModelId(dto.getLlmModelId());
        }
        if (dto.getSlmModelId() != null) {
            existingEntity.setSlmModelId(dto.getSlmModelId());
        }
        if (dto.getVllmModelId() != null) {
            existingEntity.setVllmModelId(dto.getVllmModelId());
        }
        if (dto.getTtsModelId() != null) {
            existingEntity.setTtsModelId(dto.getTtsModelId());
        }
        if (dto.getTtsVoiceId() != null) {
            existingEntity.setTtsVoiceId(dto.getTtsVoiceId());
        }
        if (dto.getTtsLanguage() != null) {
            existingEntity.setTtsLanguage(dto.getTtsLanguage());
        }
        if (dto.getTtsVolume() != null) {
            existingEntity.setTtsVolume(dto.getTtsVolume());
        }
        if (dto.getTtsRate() != null) {
            existingEntity.setTtsRate(dto.getTtsRate());
        }
        if (dto.getTtsPitch() != null) {
            existingEntity.setTtsPitch(dto.getTtsPitch());
        }
        if (dto.getMemModelId() != null) {
            existingEntity.setMemModelId(dto.getMemModelId());
        }
        if (dto.getIntentModelId() != null) {
            existingEntity.setIntentModelId(dto.getIntentModelId());
        }
        if (dto.getSystemPrompt() != null) {
            existingEntity.setSystemPrompt(dto.getSystemPrompt());
        }
        if (dto.getSummaryMemory() != null) {
            existingEntity.setSummaryMemory(dto.getSummaryMemory());
        }
        if (dto.getChatHistoryConf() != null) {
            existingEntity.setChatHistoryConf(dto.getChatHistoryConf());
        }
        if (dto.getLangCode() != null) {
            existingEntity.setLangCode(dto.getLangCode());
        }
        if (dto.getLanguage() != null) {
            existingEntity.setLanguage(dto.getLanguage());
        }
        if (dto.getSort() != null) {
            existingEntity.setSort(dto.getSort());
        }

        // Update function plugin info
        List<AgentUpdateDTO.FunctionInfo> functions = dto.getFunctions();
        if (functions != null) {
            // 1. Collect pluginId for this commit
            List<String> newPluginIds = functions.stream()
                    .map(AgentUpdateDTO.FunctionInfo::getPluginId)
                    .toList();

            // 2. Query all existing mappings for the current agent
            List<AgentPluginMapping> existing = agentPluginMappingService.list(
                    new QueryWrapper<AgentPluginMapping>()
                            .eq("agent_id", agentId));
            Map<String, AgentPluginMapping> existMap = existing.stream()
                    .collect(Collectors.toMap(AgentPluginMapping::getPluginId, Function.identity()));

            // 3. Construct all entities to save or update
            List<AgentPluginMapping> allToPersist = functions.stream().map(info -> {
                AgentPluginMapping m = new AgentPluginMapping();
                m.setAgentId(agentId);
                m.setPluginId(info.getPluginId());
                m.setParamInfo(JsonUtils.toJsonString(info.getParamInfo()));
                AgentPluginMapping old = existMap.get(info.getPluginId());
                if (old != null) {
                    // Already exists, setting id indicates update
                    m.setId(old.getId());
                }
                return m;
            }).toList();

            // 4. Split: update existing IDs, insert new ones
            List<AgentPluginMapping> toUpdate = allToPersist.stream()
                    .filter(m -> m.getId() != null)
                    .toList();
            List<AgentPluginMapping> toInsert = allToPersist.stream()
                    .filter(m -> m.getId() == null)
                    .toList();

            if (!toUpdate.isEmpty()) {
                agentPluginMappingService.updateBatchById(toUpdate, IRepository.DEFAULT_BATCH_SIZE);
            }
            if (!toInsert.isEmpty()) {
                agentPluginMappingService.saveBatch(toInsert, IRepository.DEFAULT_BATCH_SIZE);
            }

            // 5. Remove plugin mappings not included in this commit list
            List<Long> toDelete = existing.stream()
                    .filter(old -> !newPluginIds.contains(old.getPluginId()))
                    .map(AgentPluginMapping::getId)
                    .toList();
            if (!toDelete.isEmpty()) {
                agentPluginMappingService.removeByIds(toDelete);
            }
        }

        // Set updater info
        UserDetail user = SecurityUser.getUser();
        existingEntity.setUpdater(user.getId());
        existingEntity.setUpdatedAt(new Date());

        // Update memory policy
        // Delete all records
        if (existingEntity.getMemModelId() != null && existingEntity.getMemModelId().equals(Constant.MEMORY_NO_MEM)) {
            agentChatHistoryService.deleteByAgentId(existingEntity.getId(), true, true);
            existingEntity.setSummaryMemory("");
            // Delete memory
        } else if (existingEntity.getMemModelId() != null
                && existingEntity.getMemModelId().equals(Constant.MEMORY_MEM_REPORT_ONLY)) {
            existingEntity.setSummaryMemory("");
        }

        // Update context source config
        if (dto.getContextProviders() != null) {
            AgentContextProviderEntity contextEntity = new AgentContextProviderEntity();
            contextEntity.setAgentId(agentId);
            contextEntity.setContextProviders(dto.getContextProviders());
            agentContextProviderService.saveOrUpdateByAgentId(contextEntity);
        }

        // Update replacement word file associations
        if (dto.getCorrectWordFileIds() != null) {
            correctWordFileService.saveAgentCorrectWords(agentId, dto.getCorrectWordFileIds());
        }

        // Update agent tag
        if (dto.getTagNames() != null || dto.getTagIds() != null) {
            agentTagService.saveAgentTags(agentId, dto.getTagIds(), dto.getTagNames());
        }

        boolean b = validateLLMIntentParams(existingEntity.getLlmModelId(), existingEntity.getIntentModelId());
        if (!b) {
            throw new RenException(ErrorCode.LLM_INTENT_PARAMS_MISMATCH);
        }
        this.updateById(existingEntity);
        if (createSnapshot) {
            agentSnapshotService.createSnapshot(agentId, "config");
        }
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void updateAgentMemoryByDeviceMacAddress(String macAddress, AgentMemoryDTO dto, Long userId) {
        DeviceEntity device = deviceService.getDeviceByMacAddress(macAddress);
        if (device == null || StringUtils.isBlank(device.getAgentId()) || dto == null) {
            return;
        }

        requireDevicePermission(device, userId);

        AgentUpdateDTO agentUpdateDTO = new AgentUpdateDTO();
        agentUpdateDTO.setSummaryMemory(dto.getSummaryMemory());
        updateAgentById(device.getAgentId(), agentUpdateDTO, userId, false);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deleteAgentById(String agentId, Long userId) {
        AgentEntity agent = getAgentEntityOrThrow(agentId);
        requireAgentPermission(agent, userId);
        deleteAgent(agentId);
    }

    /**
     * Validate parameters for LLM and intent recognition
     * 
     * @param llmModelId    LLM model id
     * @param intentModelId Intent recognition ID
     * @return T match : F no match
     */
    private boolean validateLLMIntentParams(String llmModelId, String intentModelId) {
        if (StringUtils.isBlank(llmModelId)) {
            return true;
        }
        ModelConfigEntity llmModelData = modelConfigService.selectById(llmModelId);
        String type = llmModelData.getConfigJson().get("type").toString();
        // If the LLM is OpenAI or Ollama, any intent recognition parameter is acceptable
        if ("openai".equals(type) || "ollama".equals(type)) {
            return true;
        }
        // Except for openai and ollama types, do not select the intent recognition with id Intent_function_call (function call)
        return !"Intent_function_call".equals(intentModelId);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public String createAgent(AgentCreateDTO dto) {
        // Convert to entity
        AgentEntity entity = ConvertUtils.sourceToTarget(dto, AgentEntity.class);

        // Get default template
        AgentTemplateEntity template = agentTemplateService.getDefaultTemplate();
        if (template != null) {
            // Set default values in template
            entity.setAsrModelId(template.getAsrModelId());
            entity.setVadModelId(template.getVadModelId());
            entity.setLlmModelId(template.getLlmModelId());
            entity.setVllmModelId(template.getVllmModelId());
            entity.setTtsModelId(template.getTtsModelId());

            if (template.getTtsVoiceId() == null && template.getTtsModelId() != null) {
                ModelConfigEntity ttsModel = modelConfigService.selectById(template.getTtsModelId());
                if (ttsModel != null && ttsModel.getConfigJson() != null) {
                    Map<String, Object> config = ttsModel.getConfigJson();
                    String voice = (String) config.get("voice");
                    if (StringUtils.isBlank(voice)) {
                        voice = (String) config.get("speaker");
                    }
                    VoiceDTO timbre = timbreModelService.getByVoiceCode(template.getTtsModelId(), voice);
                    if (timbre != null) {
                        template.setTtsVoiceId(timbre.getId());
                    }
                }
            }

            entity.setTtsVoiceId(template.getTtsVoiceId());
            entity.setTtsLanguage(defaultIfBlank(template.getTtsLanguage(),
                    timbreModelService.getDefaultLanguageById(entity.getTtsVoiceId())));
            entity.setMemModelId(template.getMemModelId());
            entity.setIntentModelId(template.getIntentModelId());
            entity.setSystemPrompt(template.getSystemPrompt());
            entity.setSummaryMemory(template.getSummaryMemory());
            if (Constant.MEMORY_NO_MEM.equals(entity.getMemModelId())
                    || Constant.MEMORY_MEM_REPORT_ONLY.equals(entity.getMemModelId())) {
                entity.setSummaryMemory("");
            }

            // Set the default chatHistoryConf value based on the memory model type
            if (template.getMemModelId() != null) {
                if (template.getMemModelId().equals("Memory_nomem")) {
                    // Models without memory do not record chat history by default
                    entity.setChatHistoryConf(0);
                } else {
                    // Models with memory record text and voice by default
                    entity.setChatHistoryConf(2);
                }
            } else {
                entity.setChatHistoryConf(template.getChatHistoryConf());
            }

            entity.setLangCode(template.getLangCode());
            entity.setLanguage(template.getLanguage());
        }

        if (entity.getSlmModelId() == null) {
            String defaultSlmModelId = getDefaultLLMModelId();
            if (defaultSlmModelId != null) {
                entity.setSlmModelId(defaultSlmModelId);
            }
        }

        // Set user ID and creator info
        UserDetail user = SecurityUser.getUser();
        entity.setUserId(user.getId());
        entity.setCreator(user.getId());
        entity.setCreatedAt(new Date());

        // Save Agent
        insert(entity);

        // Set Default Plugin
        List<AgentPluginMapping> toInsert = new ArrayList<>();
        // Play music, check weather, check news
        String[] pluginIds = new String[] { "SYSTEM_PLUGIN_MUSIC", "SYSTEM_PLUGIN_WEATHER",
                "SYSTEM_PLUGIN_NEWS_NEWSNOW" };
        for (String pluginId : pluginIds) {
            ModelProviderDTO provider = modelProviderService.getById(pluginId);
            if (provider == null) {
                continue;
            }
            AgentPluginMapping mapping = new AgentPluginMapping();
            mapping.setPluginId(pluginId);

            Map<String, Object> paramInfo = new HashMap<>();
            List<Map<String, Object>> fields = JsonUtils.parseMapList(provider.getFields());
            if (fields != null) {
                for (Map<String, Object> field : fields) {
                    paramInfo.put((String) field.get("key"), field.get("default"));
                }
            }
            mapping.setParamInfo(JsonUtils.toJsonString(paramInfo));
            mapping.setAgentId(entity.getId());
            toInsert.add(mapping);
        }
        // Save default plugin
        agentPluginMappingService.saveBatch(toInsert, IRepository.DEFAULT_BATCH_SIZE);
        agentSnapshotService.createSnapshot(entity.getId(), "initial");
        return entity.getId();
    }

    private String defaultIfBlank(String value, String defaultValue) {
        return StringUtils.isBlank(value) ? defaultValue : value;
    }

    private String getDefaultLLMModelId() {
        try {
            List<ModelConfigEntity> llmConfigs = modelConfigService.getEnabledModelsByType("LLM");
            if (llmConfigs == null || llmConfigs.isEmpty()) {
                return null;
            }

            for (ModelConfigEntity config : llmConfigs) {
                if (config.getIsDefault() != null && config.getIsDefault() == 1) {
                    return config.getId();
                }
            }

            return llmConfigs.get(0).getId();
        } catch (Exception e) {
            return null;
        }
    }

}
