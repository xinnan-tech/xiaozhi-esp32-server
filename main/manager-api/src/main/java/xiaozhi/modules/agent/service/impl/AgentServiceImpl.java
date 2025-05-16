package xiaozhi.modules.agent.service.impl;

import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;

import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.UpdateWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;

import lombok.AllArgsConstructor;
import xiaozhi.common.constant.Constant;
import xiaozhi.common.page.PageData;
import xiaozhi.common.redis.RedisKeys;
import xiaozhi.common.redis.RedisUtils;
import xiaozhi.common.service.impl.BaseServiceImpl;
import xiaozhi.modules.agent.dao.AgentDao;
import xiaozhi.modules.agent.dto.AgentDTO;
import xiaozhi.modules.agent.entity.AgentEntity;
import xiaozhi.modules.agent.service.AgentService;
import xiaozhi.modules.device.service.DeviceService;
import xiaozhi.modules.model.service.ModelConfigService;
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

    @Override
    public PageData<AgentEntity> adminAgentList(Map<String, Object> params) {
        IPage<AgentEntity> page = agentDao.selectPage(
                getPage(params, "agent_name", true),
                new QueryWrapper<>());
        return new PageData<>(page.getRecords(), page.getTotal());
    }

    @Override
    public AgentEntity getAgentById(String id) {
        AgentEntity agent = agentDao.selectById(id);
        if (agent != null && agent.getMemModelId() != null && agent.getMemModelId().equals(Constant.MEMORY_NO_MEM)) {
            agent.setChatHistoryConf(Constant.ChatHistoryConfEnum.IGNORE.getCode());
        } else if (agent != null && agent.getMemModelId() != null
                && !agent.getMemModelId().equals(Constant.MEMORY_NO_MEM)
                && agent.getChatHistoryConf() == null) {
            agent.setChatHistoryConf(Constant.ChatHistoryConfEnum.RECORD_TEXT_AUDIO.getCode());
        }
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
    public List<AgentDTO> getUserAgents(Long userId) {
        QueryWrapper<AgentEntity> wrapper = new QueryWrapper<>();
        wrapper.eq("user_id", userId);
        List<AgentEntity> agents = agentDao.selectList(wrapper);
        return agents.stream().map(agent -> {
            AgentDTO dto = new AgentDTO();
            dto.setId(agent.getId());
            dto.setAgentName(agent.getAgentName());
            dto.setSystemPrompt(agent.getSystemPrompt());

            // 获取 TTS 模型名称
            dto.setTtsModelName(modelConfigService.getModelNameById(agent.getTtsModelId()));

            // 获取 LLM 模型名称
            dto.setLlmModelName(modelConfigService.getModelNameById(agent.getLlmModelId()));

            // 获取记忆模型名称
            dto.setMemModelId(agent.getMemModelId());

            // 获取 TTS 音色名称
            dto.setTtsVoiceName(timbreModelService.getTimbreNameById(agent.getTtsVoiceId()));

            // 获取智能体最近的最后连接时长
            dto.setLastConnectedAt(deviceService.getLatestLastConnectionTime(agent.getId()));

            // 获取设备数量
            dto.setDeviceCount(getDeviceCountByAgentId(agent.getId()));
            return dto;
        }).collect(Collectors.toList());
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
}
