package xiaozhi.modules.config.service.impl;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Service;

import lombok.AllArgsConstructor;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.redis.RedisKeys;
import xiaozhi.common.redis.RedisUtils;
import xiaozhi.common.utils.JsonUtils;
import xiaozhi.modules.agent.entity.AgentEntity;
import xiaozhi.modules.agent.entity.AgentTemplateEntity;
import xiaozhi.modules.agent.service.AgentService;
import xiaozhi.modules.agent.service.AgentTemplateService;
import xiaozhi.modules.config.service.ConfigService;
import xiaozhi.modules.device.entity.DeviceEntity;
import xiaozhi.modules.device.service.DeviceService;
import xiaozhi.modules.model.entity.ModelConfigEntity;
import xiaozhi.modules.model.service.ModelConfigService;
import xiaozhi.modules.sys.dto.SysParamsDTO;
import xiaozhi.modules.sys.service.SysParamsService;

@Service
@AllArgsConstructor
public class ConfigServiceImpl implements ConfigService {
    private final SysParamsService sysParamsService;
    private final DeviceService deviceService;
    private final ModelConfigService modelConfigService;
    private final AgentService agentService;
    private final AgentTemplateService agentTemplateService;
    private final RedisUtils redisUtils;

    @Override
    public Object getConfig(Boolean isCache) {
        if (isCache) {
            // 先从Redis获取配置
            Object cachedConfig = redisUtils.get(RedisKeys.getServerConfigKey());
            if (cachedConfig != null) {
                return cachedConfig;
            }
        }

        // 构建配置信息
        Map<String, Object> result = new HashMap<>();
        buildConfig(result);

        // 查询默认智能体
        AgentTemplateEntity agent = agentTemplateService.getDefaultTemplate();
        if (agent == null) {
            throw new RenException("默认智能体未找到");
        }

        // 构建模块配置
        buildModuleConfig(
                agent.getSystemPrompt(),
                agent.getVadModelId(),
                agent.getAsrModelId(),
                agent.getLlmModelId(),
                agent.getTtsModelId(),
                agent.getMemModelId(),
                agent.getIntentModelId(),
                result,
                isCache);

        // 将配置存入Redis
        redisUtils.set(RedisKeys.getServerConfigKey(), result);

        return result;
    }

    @Override
    public Map<String, Object> getAgentModels(String macAddress) {
        // 根据MAC地址查找设备
        DeviceEntity device = deviceService.getDeviceByMacAddress(macAddress);
        if (device == null) {
            throw new RenException("设备未找到");
        }
        // 获取智能体信息
        AgentEntity agent = agentService.getAgentById(device.getAgentId());
        if (agent == null) {
            throw new RenException("智能体未找到");
        }
        // 构建返回数据
        Map<String, Object> result = new HashMap<>();

        // 构建模块配置
        buildModuleConfig(
                agent.getSystemPrompt(),
                agent.getVadModelId(),
                agent.getAsrModelId(),
                agent.getLlmModelId(),
                agent.getTtsModelId(),
                agent.getMemModelId(),
                agent.getIntentModelId(),
                result,
                true);

        return result;
    }

    /**
     * 构建配置信息
     * 
     * @param paramsList 系统参数列表
     * @return 配置信息
     */
    @SuppressWarnings("unchecked")
    private Object buildConfig(Map<String, Object> config) {

        // 查询所有系统参数
        List<SysParamsDTO> paramsList = sysParamsService.list(new HashMap<>());

        for (SysParamsDTO param : paramsList) {
            String[] keys = param.getParamCode().split("\\.");
            Map<String, Object> current = config;

            // 遍历除最后一个key之外的所有key
            for (int i = 0; i < keys.length - 1; i++) {
                String key = keys[i];
                if (!current.containsKey(key)) {
                    current.put(key, new HashMap<String, Object>());
                }
                current = (Map<String, Object>) current.get(key);
            }

            // 处理最后一个key
            String lastKey = keys[keys.length - 1];
            String value = param.getParamValue();

            // 根据valueType转换值
            switch (param.getValueType().toLowerCase()) {
                case "number":
                    try {
                        current.put(lastKey, Double.parseDouble(value));
                    } catch (NumberFormatException e) {
                        current.put(lastKey, value);
                    }
                    break;
                case "boolean":
                    current.put(lastKey, Boolean.parseBoolean(value));
                    break;
                case "array":
                    // 将分号分隔的字符串转换为数字数组
                    List<String> list = new ArrayList<>();
                    for (String num : value.split(";")) {
                        if (StringUtils.isNotBlank(num)) {
                            list.add(num.trim());
                        }
                    }
                    current.put(lastKey, list);
                    break;
                case "json":
                    try {
                        current.put(lastKey, JsonUtils.parseObject(value, Object.class));
                    } catch (Exception e) {
                        current.put(lastKey, value);
                    }
                    break;
                default:
                    current.put(lastKey, value);
            }
        }

        return config;
    }

    /**
     * 构建模块配置
     * 
     * @param vadModelId    VAD模型ID
     * @param asrModelId    ASR模型ID
     * @param llmModelId    LLM模型ID
     * @param ttsModelId    TTS模型ID
     * @param memModelId    记忆模型ID
     * @param intentModelId 意图模型ID
     * @param result        结果Map
     */
    private void buildModuleConfig(
            String prompt,
            String vadModelId,
            String asrModelId,
            String llmModelId,
            String ttsModelId,
            String memModelId,
            String intentModelId,
            Map<String, Object> result,
            boolean isCache) {
        Map<String, String> selectedModule = new HashMap<>();

        String[] modelTypes = { "VAD", "ASR", "LLM", "TTS", "Memory", "Intent" };
        String[] modelIds = { vadModelId, asrModelId, llmModelId, ttsModelId, memModelId, intentModelId };

        for (int i = 0; i < modelIds.length; i++) {
            ModelConfigEntity model = modelConfigService.getModelById(modelIds[i], isCache);
            Map<String, Object> typeConfig = new HashMap<>();
            typeConfig.put(model.getModelCode(), model.getConfigJson());
            result.put(modelTypes[i], typeConfig);
            selectedModule.put(modelTypes[i], model.getModelCode());
        }
        result.put("selected_module", selectedModule);
        result.put("prompt", prompt);
    }
}
