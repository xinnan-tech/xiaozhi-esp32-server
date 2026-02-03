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
import com.baomidou.mybatisplus.core.conditions.update.UpdateWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;

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
import xiaozhi.common.utils.ToolUtil;
import xiaozhi.modules.agent.dao.AgentDao;
import xiaozhi.modules.agent.dto.AgentCreateDTO;
import xiaozhi.modules.agent.dto.AgentDTO;
import xiaozhi.modules.agent.dto.AgentUpdateDTO;
import xiaozhi.modules.agent.entity.AgentContextProviderEntity;
import xiaozhi.modules.agent.entity.AgentEntity;
import xiaozhi.modules.agent.entity.AgentPluginMapping;
import xiaozhi.modules.agent.entity.AgentTemplateEntity;
import xiaozhi.modules.agent.service.AgentChatHistoryService;
import xiaozhi.modules.agent.service.AgentContextProviderService;
import xiaozhi.modules.agent.service.AgentPluginMappingService;
import xiaozhi.modules.agent.service.AgentService;
import xiaozhi.modules.agent.service.AgentTemplateService;
import xiaozhi.modules.agent.vo.AgentInfoVO;
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
    private final TimbreService timbreModelService;
    private final ModelConfigService modelConfigService;
    private final RedisUtils redisUtils;
    private final DeviceService deviceService;
    private final AgentPluginMappingService agentPluginMappingService;
    private final AgentChatHistoryService agentChatHistoryService;
    private final AgentTemplateService agentTemplateService;
    private final ModelProviderService modelProviderService;
    private final AgentContextProviderService agentContextProviderService;

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

        if (agent.getMemModelId() != null && agent.getMemModelId().equals(Constant.MEMORY_NO_MEM)) {
            agent.setChatHistoryConf(Constant.ChatHistoryConfEnum.IGNORE.getCode());
        }
        if (agent.getChatHistoryConf() == null) {
            agent.setChatHistoryConf(Constant.ChatHistoryConfEnum.RECORD_TEXT_AUDIO.getCode());
        }

        // 查询上下文源配置
        AgentContextProviderEntity contextProviderEntity = agentContextProviderService.getByAgentId(id);
        if (contextProviderEntity != null) {
            agent.setContextProviders(contextProviderEntity.getContextProviders());
        }

        // 无需额外查询插件列表，已通过SQL查询出来
        return agent;
    }

    @Override
    public boolean insert(AgentEntity entity) {
        // 如果ID为空，自动生成一个UUID作为ID
        if (entity.getId() == null || entity.getId().trim().isEmpty()) {
            entity.setId(UUID.randomUUID().toString().replace("-", ""));
        }

        // 如果智能体编码为空，自动生成一个带前缀的编码
        if (entity.getAgentCode() == null || entity.getAgentCode().trim().isEmpty()) {
            entity.setAgentCode("AGT_" + System.currentTimeMillis());
        }

        // 如果排序字段为空，设置默认值0
        if (entity.getSort() == null) {
            entity.setSort(0);
        }

        return super.insert(entity);
    }

    @Override
    public void deleteAgentByUserId(Long userId) {
        UpdateWrapper<AgentEntity> wrapper = new UpdateWrapper<>();
        wrapper.eq("user_id", userId);
        baseDao.delete(wrapper);
    }

    @Override
    public List<AgentDTO> getUserAgents(Long userId, String keyword, String searchType) {
        QueryWrapper<AgentEntity> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("user_id", userId).orderByDesc("created_at");

        // 如果有搜索关键词，根据搜索类型添加相应的查询条件
        if (StringUtils.isNotBlank(keyword)) {
            if ("mac".equals(searchType)) {
                // 按MAC地址搜索：先搜索设备，再获取对应的智能体
                List<DeviceEntity> devices = Optional
                        .ofNullable(deviceService.searchDevicesByMacAddress(keyword, userId)).orElseGet(ArrayList::new);
                // 获取设备对应的智能体ID列表
                List<String> agentIds = devices.stream()
                        .map(DeviceEntity::getAgentId)
                        .distinct()
                        .collect(Collectors.toList());
                if (ToolUtil.isNotEmpty(agentIds)) {
                    queryWrapper.in("id", agentIds);
                } else {
                    return new ArrayList<>();
                }
            } else {
                // 按名称搜索
                queryWrapper.like("agent_name", keyword);
            }
        }

        // 执行查询
        List<AgentEntity> agentEntities = baseDao.selectList(queryWrapper);

        // 转换为DTO并设置所有必要字段
        return agentEntities.stream().map(this::buildAgentDTO).collect(Collectors.toList());
    }

    /**
     * 将AgentEntity转换为AgentDTO
     */
    private AgentDTO buildAgentDTO(AgentEntity agent) {
        AgentDTO dto = new AgentDTO();
        dto.setId(agent.getId());
        dto.setAgentName(agent.getAgentName());
        dto.setSystemPrompt(agent.getSystemPrompt());

        // 获取 TTS 模型名称
        dto.setTtsModelName(modelConfigService.getModelNameById(agent.getTtsModelId()));

        // 获取 LLM 模型名称
        dto.setLlmModelName(modelConfigService.getModelNameById(agent.getLlmModelId()));

        // 获取 VLLM 模型名称
        dto.setVllmModelName(modelConfigService.getModelNameById(agent.getVllmModelId()));

        // 获取记忆模型名称
        dto.setMemModelId(agent.getMemModelId());

        // 获取 TTS 音色名称
        dto.setTtsVoiceName(timbreModelService.getTimbreNameById(agent.getTtsVoiceId()));

        // 获取智能体最近的最后连接时长
        dto.setLastConnectedAt(deviceService.getLatestLastConnectionTime(agent.getId()));

        // 获取设备数量
        dto.setDeviceCount(getDeviceCountByAgentId(agent.getId()));

        return dto;
    }

    @Override
    public Integer getDeviceCountByAgentId(String agentId) {
        if (StringUtils.isBlank(agentId)) {
            return 0;
        }

        // 先从Redis中获取
        Integer cachedCount = (Integer) redisUtils.get(RedisKeys.getAgentDeviceCountById(agentId));
        if (cachedCount != null) {
            return cachedCount;
        }

        // 如果Redis中没有，则从数据库查询
        Integer deviceCount = agentDao.getDeviceCountByAgentId(agentId);

        // 将结果存入Redis
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
        if (SecurityUser.getUser() == null || SecurityUser.getUser().getId() == null) {
            return false;
        }
        // 获取智能体信息
        AgentEntity agent = getAgentById(agentId);
        if (agent == null) {
            return false;
        }

        // 如果是超级管理员，直接返回true
        if (SecurityUser.getUser().getSuperAdmin() == SuperAdminEnum.YES.value()) {
            return true;
        }

        // 检查是否是智能体的所有者
        return userId.equals(agent.getUserId());
    }

    // 根据id更新智能体信息
    @Override
    @Transactional(rollbackFor = Exception.class)
    public void updateAgentById(String agentId, AgentUpdateDTO dto) {
        // 先查询现有实体
        AgentEntity existingEntity = this.getAgentById(agentId);
        if (existingEntity == null) {
            throw new RenException(ErrorCode.AGENT_NOT_FOUND);
        }

        // 只更新提供的非空字段
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
        if (dto.getVllmModelId() != null) {
            existingEntity.setVllmModelId(dto.getVllmModelId());
        }
        if (dto.getTtsModelId() != null) {
            existingEntity.setTtsModelId(dto.getTtsModelId());
        }
        if (dto.getTtsVoiceId() != null) {
            existingEntity.setTtsVoiceId(dto.getTtsVoiceId());
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

        // 更新函数插件信息
        List<AgentUpdateDTO.FunctionInfo> functions = dto.getFunctions();
        if (functions != null) {
            // 1. 收集本次提交的 pluginId
            List<String> newPluginIds = functions.stream()
                    .map(AgentUpdateDTO.FunctionInfo::getPluginId)
                    .toList();

            // 2. 查询当前agent现有的所有映射
            List<AgentPluginMapping> existing = agentPluginMappingService.list(
                    new QueryWrapper<AgentPluginMapping>()
                            .eq("agent_id", agentId));
            Map<String, AgentPluginMapping> existMap = existing.stream()
                    .collect(Collectors.toMap(AgentPluginMapping::getPluginId, Function.identity()));

            // 3. 构造所有要 保存或更新 的实体
            List<AgentPluginMapping> allToPersist = functions.stream().map(info -> {
                AgentPluginMapping m = new AgentPluginMapping();
                m.setAgentId(agentId);
                m.setPluginId(info.getPluginId());
                m.setParamInfo(JsonUtils.toJsonString(info.getParamInfo()));
                AgentPluginMapping old = existMap.get(info.getPluginId());
                if (old != null) {
                    // 已存在，设置id表示更新
                    m.setId(old.getId());
                }
                return m;
            }).toList();

            // 4. 拆分：已有ID的走更新，无ID的走插入
            List<AgentPluginMapping> toUpdate = allToPersist.stream()
                    .filter(m -> m.getId() != null)
                    .toList();
            List<AgentPluginMapping> toInsert = allToPersist.stream()
                    .filter(m -> m.getId() == null)
                    .toList();

            if (!toUpdate.isEmpty()) {
                agentPluginMappingService.updateBatchById(toUpdate);
            }
            if (!toInsert.isEmpty()) {
                agentPluginMappingService.saveBatch(toInsert);
            }

            // 5. 删除本次不在提交列表里的插件映射
            List<Long> toDelete = existing.stream()
                    .filter(old -> !newPluginIds.contains(old.getPluginId()))
                    .map(AgentPluginMapping::getId)
                    .toList();
            if (!toDelete.isEmpty()) {
                agentPluginMappingService.removeBatchByIds(toDelete);
            }
        }

        // 设置更新者信息
        UserDetail user = SecurityUser.getUser();
        existingEntity.setUpdater(user.getId());
        existingEntity.setUpdatedAt(new Date());

        // 更新记忆策略
        if (existingEntity.getMemModelId() == null || existingEntity.getMemModelId().equals(Constant.MEMORY_NO_MEM)) {
            // 删除所有记录
            agentChatHistoryService.deleteByAgentId(existingEntity.getId(), true, true);
            existingEntity.setSummaryMemory("");
        } else if (existingEntity.getChatHistoryConf() != null && existingEntity.getChatHistoryConf() == 1) {
            // 删除音频数据
            agentChatHistoryService.deleteByAgentId(existingEntity.getId(), true, false);
        }

        // 更新上下文源配置
        if (dto.getContextProviders() != null) {
            AgentContextProviderEntity contextEntity = new AgentContextProviderEntity();
            contextEntity.setAgentId(agentId);
            contextEntity.setContextProviders(dto.getContextProviders());
            agentContextProviderService.saveOrUpdateByAgentId(contextEntity);
        }

        // [New] 软同步校验
        if (dto.getLlmModelId() != null) {
            validateAgentConfig(dto.getLlmModelId());
        }

        // 移除旧的 validateLLMIntentParams 调用 (它依赖旧逻辑且有点硬编码)
        // boolean b = validateLLMIntentParams(dto.getLlmModelId(),
        // dto.getIntentModelId());
        // if (!b) {
        // throw new RenException(ErrorCode.LLM_INTENT_PARAMS_MISMATCH);
        // }

        this.updateById(existingEntity);
    }

    @Override
    public void validateAgentConfig(String llmModelId) {
        if (StringUtils.isBlank(llmModelId)) {
            return;
        }
        ModelConfigEntity modelConfig = modelConfigService.getModelByIdFromCache(llmModelId);
        if (modelConfig == null) {
            throw new RenException("指定的 LLM 模型不存在: " + llmModelId);
        }

        // 如果是 RAG 类型，可以进一步检查 (软同步)
        if (Constant.RAG_CONFIG_TYPE.equalsIgnoreCase(modelConfig.getModelType())) {
            // 这里可以尝试调用 RAGFlowAdapter.testConnection() 或者 simple status check
            // 为避免过度阻塞，这里只检查配置完整性 (Has BaseUrl & ApiKey)
            Map<String, Object> config = modelConfig.getConfigJson();
            if (config == null
                    || StringUtils.isBlank((String) config.get("base_url"))
                    || StringUtils.isBlank((String) config.get("api_key"))) {
                throw new RenException("RAGFlow 模型配置无效，请检查知识库配置");
            }
        }
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public String createAgent(AgentCreateDTO dto) {
        // [New] 校验 LLM 配置
        // 注意：DTO 中没有 llmModelId (DTO设计问题？AgentCreateDTO 确实没有 llmModelId)
        // 查看代码发现 createAgent 会使用默认模板覆盖。
        // 所以我们可能在应用模板后进行校验，或者如果将来 DTO 支持传入 llmModelId，则校验之。

        // 转换为实体
        AgentEntity entity = ConvertUtils.sourceToTarget(dto, AgentEntity.class);

        // 获取默认模板
        AgentTemplateEntity template = agentTemplateService.getDefaultTemplate();
        if (template != null) {
            // ... (Template copy logic same as before)
            entity.setAsrModelId(template.getAsrModelId());
            entity.setVadModelId(template.getVadModelId());
            entity.setLlmModelId(template.getLlmModelId()); // Set from template
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
            entity.setMemModelId(template.getMemModelId());
            entity.setIntentModelId(template.getIntentModelId());
            entity.setSystemPrompt(template.getSystemPrompt());
            entity.setSummaryMemory(template.getSummaryMemory());

            // 根据记忆模型类型设置默认的chatHistoryConf值
            if (template.getMemModelId() != null) {
                if (template.getMemModelId().equals("Memory_nomem")) {
                    entity.setChatHistoryConf(0);
                } else {
                    entity.setChatHistoryConf(2);
                }
            } else {
                entity.setChatHistoryConf(template.getChatHistoryConf());
            }

            entity.setLangCode(template.getLangCode());
            entity.setLanguage(template.getLanguage());
        }

        // [New] 校验最终的 LLM Model ID (来自模板)
        validateAgentConfig(entity.getLlmModelId());

        // 设置用户ID和创建者信息
        UserDetail user = SecurityUser.getUser();
        entity.setUserId(user.getId());
        entity.setCreator(user.getId());
        entity.setCreatedAt(new Date());

        // 保存智能体
        insert(entity);

        // 设置默认插件
        List<AgentPluginMapping> toInsert = new ArrayList<>();
        // 播放音乐、查天气、查新闻
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
            List<Map<String, Object>> fields = JsonUtils.parseObject(provider.getFields(), List.class);
            if (fields != null) {
                for (Map<String, Object> field : fields) {
                    paramInfo.put((String) field.get("key"), field.get("default"));
                }
            }
            mapping.setParamInfo(JsonUtils.toJsonString(paramInfo));
            mapping.setAgentId(entity.getId());
            toInsert.add(mapping);
        }
        // 保存默认插件
        agentPluginMappingService.saveBatch(toInsert);
        return entity.getId();
    }
}