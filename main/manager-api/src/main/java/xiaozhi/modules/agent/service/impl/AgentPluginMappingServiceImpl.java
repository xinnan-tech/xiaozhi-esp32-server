package xiaozhi.modules.agent.service.impl;

import java.nio.charset.StandardCharsets;
import java.security.KeyFactory;
import java.security.MessageDigest;
import java.security.PrivateKey;
import java.security.Signature;
import java.security.spec.PKCS8EncodedKeySpec;
import java.util.ArrayList;
import java.util.Base64;
import java.util.HexFormat;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Service;

import com.baomidou.mybatisplus.core.conditions.update.UpdateWrapper;
import com.baomidou.mybatisplus.spring.repository.CrudRepository;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.utils.JsonUtils;
import xiaozhi.modules.agent.dao.AgentPluginMappingMapper;
import xiaozhi.modules.agent.entity.AgentPluginMapping;
import xiaozhi.modules.agent.service.AgentPluginMappingService;
import xiaozhi.modules.knowledge.entity.KnowledgeBaseEntity;
import xiaozhi.modules.knowledge.service.KnowledgeBaseService;
import xiaozhi.modules.model.entity.ModelConfigEntity;
import xiaozhi.modules.model.service.ModelConfigService;
import xiaozhi.modules.security.secret.ProjectSecretService;

/**
 * @description 针对表【ai_agent_plugin_mapping(Agent与插件的唯一映射表)】的数据库操作Service实现
 * @createDate 2025-05-25 22:33:17
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class AgentPluginMappingServiceImpl extends CrudRepository<AgentPluginMappingMapper, AgentPluginMapping>
        implements AgentPluginMappingService {
    private static final String WEATHER_PLUGIN_ID = "SYSTEM_PLUGIN_WEATHER";
    private static final String WEATHER_PROVIDER_CODE = "get_weather";
    private static final String API_KEY = "api_key";
    private static final String PRIVATE_KEY = "private_key";
    private static final String SNAPSHOT_SECRET_PLACEHOLDER = "__SNAPSHOT_SECRET_REDACTED__";

    private final AgentPluginMappingMapper agentPluginMappingMapper;
    private final KnowledgeBaseService knowledgeBaseService;
    private final ModelConfigService modelConfigService;
    private final ProjectSecretService projectSecretService;

    @Override
    public Map<String, Object> prepareParamsForStorage(String agentId, String pluginId,
            Map<String, Object> submittedParams, String existingParamInfo) {
        Map<String, Object> submitted = submittedParams == null ? new HashMap<>() : new HashMap<>(submittedParams);
        if (!WEATHER_PLUGIN_ID.equals(pluginId)) {
            return submitted;
        }

        Map<String, Object> existing = parseParams(existingParamInfo);
        submitted.remove("api_key_configured");
        submitted.remove("private_key_configured");

        String authType = stringValue(submitted.get("auth_type"));
        if (StringUtils.isBlank(authType)) {
            authType = "api_key";
        }
        if (!"api_key".equals(authType) && !"jwt".equals(authType)) {
            throw new RenException("QWeather auth_type must be api_key or jwt");
        }
        submitted.put("auth_type", authType);

        preserveOrEncryptSecret(agentId, pluginId, API_KEY, submitted, existing, false);
        preserveOrEncryptSecret(agentId, pluginId, PRIVATE_KEY, submitted, existing, true);
        return submitted;
    }

    @Override
    public void redactCredentialsForAdmin(List<AgentPluginMapping> mappings) {
        if (mappings == null) {
            return;
        }
        mappings.stream()
                .filter(this::isWeatherMapping)
                .forEach(mapping -> {
                    Map<String, Object> params = parseParams(mapping.getParamInfo());
                    redactCredential(params, API_KEY);
                    redactCredential(params, PRIVATE_KEY);
                    mapping.setParamInfo(JsonUtils.toJsonString(params));
                });
    }

    @Override
    public String resolveParamsForServer(AgentPluginMapping mapping) {
        if (!isWeatherMapping(mapping)) {
            return mapping.getParamInfo();
        }
        Map<String, Object> params = parseParams(mapping.getParamInfo());
        resolveSecret(mapping, params, API_KEY, true);
        resolveSecret(mapping, params, PRIVATE_KEY, false);
        params.remove("api_key_configured");
        params.remove("private_key_configured");
        params.remove("private_key_fingerprint");
        return JsonUtils.toJsonString(params);
    }

    private void preserveOrEncryptSecret(String agentId, String pluginId, String field,
            Map<String, Object> submitted, Map<String, Object> existing, boolean encryptionRequired) {
        String value = stringValue(submitted.get(field));
        String existingValue = stringValue(existing.get(field));
        if (StringUtils.isBlank(value) || SNAPSHOT_SECRET_PLACEHOLDER.equals(value)) {
            if (StringUtils.isNotBlank(existingValue)) {
                submitted.put(field, existingValue);
                if (PRIVATE_KEY.equals(field) && existing.containsKey("private_key_fingerprint")) {
                    submitted.put("private_key_fingerprint", existing.get("private_key_fingerprint"));
                }
            } else {
                submitted.remove(field);
            }
            return;
        }
        if (projectSecretService.isEncrypted(value)) {
            throw new RenException("Encrypted credentials cannot be submitted directly");
        }

        String normalized = PRIVATE_KEY.equals(field) ? validateAndNormalizePrivateKey(value) : value.trim();
        if (encryptionRequired && !projectSecretService.isConfigured()) {
            throw new RenException("xiaozhi.secret.master-key is required for QWeather JWT credentials");
        }
        String stored = projectSecretService.isConfigured()
                ? projectSecretService.encrypt(normalized, purpose(field), aad(agentId, pluginId, field))
                : normalized;
        submitted.put(field, stored);
        if (PRIVATE_KEY.equals(field)) {
            submitted.put("private_key_fingerprint", fingerprint(normalized));
        }
    }

    private void resolveSecret(AgentPluginMapping mapping, Map<String, Object> params, String field,
            boolean allowLegacyPlaintext) {
        String value = stringValue(params.get(field));
        if (StringUtils.isBlank(value)) {
            params.remove(field);
            return;
        }
        try {
            if (projectSecretService.isEncrypted(value)) {
                params.put(field, projectSecretService.decrypt(value, purpose(field),
                        aad(mapping.getAgentId(), mapping.getPluginId(), field)));
            } else if (!allowLegacyPlaintext) {
                log.warn("Ignoring plaintext QWeather private key for agent {}", mapping.getAgentId());
                params.remove(field);
            }
        } catch (RuntimeException exception) {
            log.warn("Unable to resolve QWeather {} for agent {}", field, mapping.getAgentId());
            params.remove(field);
        }
    }

    private void redactCredential(Map<String, Object> params, String field) {
        boolean configured = StringUtils.isNotBlank(stringValue(params.remove(field)));
        params.put(field + "_configured", configured);
        params.put(field, "");
    }

    private boolean isWeatherMapping(AgentPluginMapping mapping) {
        return mapping != null && (WEATHER_PLUGIN_ID.equals(mapping.getPluginId())
                || WEATHER_PROVIDER_CODE.equals(mapping.getProviderCode()));
    }

    private Map<String, Object> parseParams(String paramInfo) {
        if (StringUtils.isBlank(paramInfo)) {
            return new HashMap<>();
        }
        Map<String, Object> parsed = JsonUtils.toStringObjectMap(JsonUtils.parseObject(paramInfo, Map.class));
        return parsed == null ? new HashMap<>() : new HashMap<>(parsed);
    }

    private String validateAndNormalizePrivateKey(String pem) {
        String normalized = pem.replace("\r\n", "\n").trim();
        String begin = "-----BEGIN PRIVATE KEY-----";
        String end = "-----END PRIVATE KEY-----";
        if (!normalized.startsWith(begin) || !normalized.endsWith(end)) {
            throw new RenException("QWeather private key must be an Ed25519 PKCS#8 PEM");
        }
        try {
            String base64 = normalized.substring(begin.length(), normalized.length() - end.length())
                    .replaceAll("\\s", "");
            byte[] der = Base64.getDecoder().decode(base64);
            PrivateKey privateKey = KeyFactory.getInstance("Ed25519")
                    .generatePrivate(new PKCS8EncodedKeySpec(der));
            Signature signature = Signature.getInstance("Ed25519");
            signature.initSign(privateKey);
            signature.update("xiaozhi-qweather-key-check".getBytes(StandardCharsets.UTF_8));
            signature.sign();
            return normalized + "\n";
        } catch (Exception exception) {
            throw new RenException("QWeather private key must be an Ed25519 PKCS#8 PEM", exception);
        }
    }

    private String fingerprint(String value) {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(digest, 0, 8);
        } catch (Exception exception) {
            throw new IllegalStateException("Unable to fingerprint QWeather private key", exception);
        }
    }

    private String purpose(String field) {
        return "agent-plugin-secret:v1:" + WEATHER_PROVIDER_CODE + ":" + field;
    }

    private String aad(String agentId, String pluginId, String field) {
        return String.join("|", StringUtils.defaultString(agentId), StringUtils.defaultString(pluginId), field);
    }

    private String stringValue(Object value) {
        return value == null ? null : String.valueOf(value);
    }

    @Override
    public List<AgentPluginMapping> agentPluginParamsByAgentId(String agentId) {
        List<AgentPluginMapping> list = agentPluginMappingMapper.selectPluginsByAgentId(agentId);
        Map<String, List<KnowledgeBaseEntity>> knowledgeBaseMap = new HashMap<>();
        Map<String, ModelConfigEntity> modelConfigMap = new HashMap<>();
        for (int i = list.size() - 1; i >= 0; i--) {
            AgentPluginMapping mapping = list.get(i);
            if (StringUtils.isBlank(mapping.getProviderCode())) {
                // 查询知识库插件参数
                KnowledgeBaseEntity knowledgeBaseEntity = knowledgeBaseService.selectById(mapping.getPluginId());
                if (knowledgeBaseEntity == null) {
                    list.remove(i);
                    continue;
                }
                ModelConfigEntity modelConfigEntity = modelConfigService
                        .getModelByIdFromCache(knowledgeBaseEntity.getRagModelId());
                if (modelConfigEntity == null) {
                    list.remove(i);
                    continue;
                }
                List<KnowledgeBaseEntity> knowledgeBaseList = knowledgeBaseMap.get(modelConfigEntity.getModelCode());
                if (knowledgeBaseList == null) {
                    knowledgeBaseList = new ArrayList<>();
                }
                modelConfigMap.put(modelConfigEntity.getModelCode(), modelConfigEntity);
                knowledgeBaseList.add(knowledgeBaseEntity);
                knowledgeBaseMap.put(modelConfigEntity.getModelCode(), knowledgeBaseList);
                list.remove(i);
            }
        }
        if (knowledgeBaseMap.size() > 0) {
            for (String pluginCode : knowledgeBaseMap.keySet()) {
                List<KnowledgeBaseEntity> knowledgeBaseList = knowledgeBaseMap.get(pluginCode);
                if (knowledgeBaseList == null || knowledgeBaseList.isEmpty()) {
                    continue;
                }

                AgentPluginMapping agentPluginMapping = new AgentPluginMapping();
                agentPluginMapping.setAgentId(agentId);
                agentPluginMapping.setPluginId(pluginCode);
                agentPluginMapping.setProviderCode("search_from_" + pluginCode);
                agentPluginMapping.setId(Long.valueOf(list.size() + 1));

                Map<String, Object> paramInfo = new HashMap<>(4);
                ModelConfigEntity modelConfigEntity = modelConfigMap.get(pluginCode);
                paramInfo.put("base_url", modelConfigEntity.getConfigJson().getStr("base_url"));
                paramInfo.put("api_key", modelConfigEntity.getConfigJson().getStr("api_key"));
                paramInfo.put("dataset_ids",
                        knowledgeBaseList.stream().map(KnowledgeBaseEntity::getDatasetId).toList());

                String description = "如果用户询问与【"
                        + String.join(",", knowledgeBaseList.stream().map(KnowledgeBaseEntity::getName).toList())
                        + "】涵盖的主体范围相关内容时应调用本方法，用于查询：" + String.join(",",
                                knowledgeBaseList.stream().map(KnowledgeBaseEntity::getDescription).toList());
                paramInfo.put("description", description);
                agentPluginMapping.setParamInfo(JsonUtils.toJsonString(paramInfo));
                list.add(agentPluginMapping);
            }
        }
        return list;
    }

    @Override
    public void deleteByAgentId(String agentId) {
        UpdateWrapper<AgentPluginMapping> updateWrapper = new UpdateWrapper<>();
        updateWrapper.eq("agent_id", agentId);
        agentPluginMappingMapper.delete(updateWrapper);
    }

    @Override
    public void deleteByPluginId(String pluginId) {
        UpdateWrapper<AgentPluginMapping> updateWrapper = new UpdateWrapper<>();
        updateWrapper.eq("plugin_id", pluginId);
        agentPluginMappingMapper.delete(updateWrapper);
    }

}
