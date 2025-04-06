package xiaozhi.modules.agent.service.impl;

import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;

import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.UpdateWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;

import xiaozhi.common.page.PageData;
import xiaozhi.common.redis.RedisKeys;
import xiaozhi.common.redis.RedisUtils;
import xiaozhi.common.service.impl.BaseServiceImpl;
import xiaozhi.modules.agent.dao.AgentDao;
import xiaozhi.modules.agent.dto.AgentDTO;
import xiaozhi.modules.agent.entity.AgentEntity;
import xiaozhi.modules.agent.service.AgentService;
import xiaozhi.modules.model.service.ModelConfigService;
import xiaozhi.modules.timbre.service.TimbreService;

@Service
public class AgentServiceImpl extends BaseServiceImpl<AgentDao, AgentEntity> implements AgentService {
    private final AgentDao agentDao;

    @Autowired
    private TimbreService timbreModelService;

    @Autowired
    private ModelConfigService modelConfigService;

    @Autowired
    private RedisUtils redisUtils;

    public AgentServiceImpl(AgentDao agentDao) {
        this.agentDao = agentDao;
    }

    @Override
    public PageData<AgentEntity> adminAgentList(Map<String, Object> params) {
        IPage<AgentEntity> page = agentDao.selectPage(
                getPage(params, "sort", true),
                new QueryWrapper<>());
        return new PageData<>(page.getRecords(), page.getTotal());
    }

    @Override
    public AgentEntity getAgentById(String id) {
        return agentDao.selectById(id);
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

            // 获取 TTS 音色名称
            dto.setTtsVoiceName(timbreModelService.getTimbreNameById(agent.getTtsVoiceId()));

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
}