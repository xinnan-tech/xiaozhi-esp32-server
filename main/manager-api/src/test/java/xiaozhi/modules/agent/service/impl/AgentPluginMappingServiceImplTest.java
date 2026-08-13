package xiaozhi.modules.agent.service.impl;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.mock;

import java.security.KeyPairGenerator;
import java.util.Base64;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.Test;

import xiaozhi.common.exception.RenException;
import xiaozhi.common.utils.JsonUtils;
import xiaozhi.modules.agent.dao.AgentPluginMappingMapper;
import xiaozhi.modules.agent.entity.AgentPluginMapping;
import xiaozhi.modules.knowledge.service.KnowledgeBaseService;
import xiaozhi.modules.model.service.ModelConfigService;
import xiaozhi.modules.security.secret.ProjectSecretService;

class AgentPluginMappingServiceImplTest {
    private static final String AGENT_ID = "agent-a";
    private static final String PLUGIN_ID = "SYSTEM_PLUGIN_WEATHER";

    @Test
    void encryptsJwtPrivateKeyAndResolvesItOnlyForServerConfig() throws Exception {
        AgentPluginMappingServiceImpl service = newService(masterKey());
        String privateKey = privateKeyPem();
        Map<String, Object> submitted = new HashMap<>();
        submitted.put("auth_type", "jwt");
        submitted.put("project_id", "project");
        submitted.put("credential_id", "credential");
        submitted.put("private_key", privateKey);

        Map<String, Object> stored = service.prepareParamsForStorage(AGENT_ID, PLUGIN_ID, submitted, null);

        String envelope = String.valueOf(stored.get("private_key"));
        assertTrue(envelope.startsWith("enc:v1:a256gcm:"));
        assertFalse(envelope.contains("BEGIN PRIVATE KEY"));
        assertTrue(String.valueOf(stored.get("private_key_fingerprint")).matches("[0-9a-f]{16}"));

        AgentPluginMapping mapping = weatherMapping(JsonUtils.toJsonString(stored));
        Map<String, Object> runtime = JsonUtils.parseMap(service.resolveParamsForServer(mapping));
        assertEquals(privateKey.trim(), String.valueOf(runtime.get("private_key")).trim());
        assertFalse(runtime.containsKey("private_key_fingerprint"));

        service.redactCredentialsForAdmin(List.of(mapping));
        Map<String, Object> admin = JsonUtils.parseMap(mapping.getParamInfo());
        assertEquals("", admin.get("private_key"));
        assertEquals(true, admin.get("private_key_configured"));
        assertFalse(mapping.getParamInfo().contains("enc:v1"));
    }

    @Test
    void preservesStoredCredentialsWhenAdminSubmitsMaskedBlankValues() throws Exception {
        AgentPluginMappingServiceImpl service = newService(masterKey());
        Map<String, Object> first = service.prepareParamsForStorage(
                AGENT_ID,
                PLUGIN_ID,
                Map.of("auth_type", "jwt", "private_key", privateKeyPem()),
                null);
        Map<String, Object> masked = new HashMap<>();
        masked.put("auth_type", "jwt");
        masked.put("private_key", "");
        masked.put("private_key_configured", true);

        Map<String, Object> saved = service.prepareParamsForStorage(
                AGENT_ID, PLUGIN_ID, masked, JsonUtils.toJsonString(first));

        assertEquals(first.get("private_key"), saved.get("private_key"));
        assertEquals(first.get("private_key_fingerprint"), saved.get("private_key_fingerprint"));
        assertFalse(saved.containsKey("private_key_configured"));
    }

    @Test
    void keepsLegacyApiKeyWorkingWithoutMasterKeyButRejectsJwtPrivateKey() throws Exception {
        AgentPluginMappingServiceImpl service = newService("");

        Map<String, Object> apiKey = service.prepareParamsForStorage(
                AGENT_ID, PLUGIN_ID, Map.of("auth_type", "api_key", "api_key", "legacy"), null);

        assertEquals("legacy", apiKey.get("api_key"));
        assertThrows(RenException.class,
                () -> service.prepareParamsForStorage(
                        AGENT_ID, PLUGIN_ID, Map.of("auth_type", "jwt", "private_key", privateKeyPem()), null));
    }

    private static AgentPluginMappingServiceImpl newService(String masterKey) {
        return new AgentPluginMappingServiceImpl(
                mock(AgentPluginMappingMapper.class),
                mock(KnowledgeBaseService.class),
                mock(ModelConfigService.class),
                new ProjectSecretService(masterKey));
    }

    private static AgentPluginMapping weatherMapping(String paramInfo) {
        AgentPluginMapping mapping = new AgentPluginMapping();
        mapping.setAgentId(AGENT_ID);
        mapping.setPluginId(PLUGIN_ID);
        mapping.setProviderCode("get_weather");
        mapping.setParamInfo(paramInfo);
        return mapping;
    }

    private static String masterKey() {
        byte[] key = new byte[32];
        for (int index = 0; index < key.length; index++) {
            key[index] = (byte) index;
        }
        return Base64.getEncoder().encodeToString(key);
    }

    private static String privateKeyPem() throws Exception {
        byte[] der = KeyPairGenerator.getInstance("Ed25519").generateKeyPair().getPrivate().getEncoded();
        String base64 = Base64.getMimeEncoder(64, new byte[] { '\n' }).encodeToString(der);
        return "-----BEGIN PRIVATE KEY-----\n" + base64 + "\n-----END PRIVATE KEY-----\n";
    }
}
