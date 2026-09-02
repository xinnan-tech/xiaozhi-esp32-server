package xiaozhi.modules.agent.service.impl;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.argThat;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.inOrder;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.verifyNoMoreInteractions;
import static org.mockito.Mockito.when;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.repository.IRepository;
import com.fasterxml.jackson.core.type.TypeReference;
import java.lang.reflect.Method;
import java.lang.reflect.InvocationTargetException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Date;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.mockito.InOrder;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.transaction.annotation.Transactional;

import xiaozhi.common.utils.JsonUtils;
import xiaozhi.common.exception.RenException;
import xiaozhi.modules.agent.Enums.AgentSnapshotField;
import xiaozhi.modules.agent.dao.AgentDao;
import xiaozhi.modules.agent.dao.AgentSnapshotDao;
import xiaozhi.modules.agent.dao.AgentTagDao;
import xiaozhi.modules.agent.dao.AgentTagRelationDao;
import xiaozhi.modules.agent.dto.AgentCreateDTO;
import xiaozhi.modules.agent.dto.AgentSnapshotDataDTO;
import xiaozhi.modules.agent.dto.AgentSnapshotPageDTO;
import xiaozhi.modules.agent.dto.AgentSnapshotTagDTO;
import xiaozhi.modules.agent.dto.AgentUpdateDTO;
import xiaozhi.modules.agent.dto.ContextProviderDTO;
import xiaozhi.modules.agent.entity.AgentEntity;
import xiaozhi.modules.agent.entity.AgentPluginMapping;
import xiaozhi.modules.agent.entity.AgentTemplateEntity;
import xiaozhi.modules.agent.entity.AgentSnapshotEntity;
import xiaozhi.modules.agent.entity.AgentTagEntity;
import xiaozhi.modules.agent.service.AgentChatHistoryService;
import xiaozhi.modules.agent.service.AgentPluginMappingService;
import xiaozhi.modules.agent.service.AgentContextProviderService;
import xiaozhi.modules.agent.service.AgentSnapshotService;
import xiaozhi.modules.agent.service.AgentTagService;
import xiaozhi.modules.agent.service.AgentTemplateService;
import xiaozhi.modules.agent.vo.AgentSnapshotVO;
import xiaozhi.modules.agent.vo.AgentInfoVO;
import xiaozhi.modules.correctword.service.CorrectWordFileService;
import xiaozhi.modules.model.service.ModelProviderService;
import xiaozhi.modules.timbre.service.TimbreService;

class AgentSnapshotServiceImplTest {

    @Test
    @SuppressWarnings("unchecked")
    void normalizeJsonListTreatsDtoAndMapShapesEqually() throws Exception {
        AgentSnapshotServiceImpl service = new AgentSnapshotServiceImpl(null, null, null, null, null, null, null, null,
                null, null);
        Method method = AgentSnapshotServiceImpl.class.getDeclaredMethod("normalizeJsonList", List.class);
        method.setAccessible(true);

        ContextProviderDTO dto = new ContextProviderDTO();
        dto.setUrl("https://example.com/context");
        dto.setHeaders(Map.of("Authorization", "Bearer token"));

        Map<String, Object> map = new LinkedHashMap<>();
        map.put("headers", Map.of("Authorization", "Bearer token"));
        map.put("url", "https://example.com/context");

        assertEquals(method.invoke(service, List.of(dto)), method.invoke(service, List.of(map)));
    }

    @Test
    @SuppressWarnings("unchecked")
    void contextProviderOrderIsARealSnapshotChange() throws Exception {
        AgentSnapshotServiceImpl service = new AgentSnapshotServiceImpl(null, null, null, null, null, null, null, null,
                null, null);
        Method method = AgentSnapshotServiceImpl.class.getDeclaredMethod("getChangedFields",
                AgentSnapshotDataDTO.class, AgentSnapshotDataDTO.class);
        method.setAccessible(true);

        ContextProviderDTO first = new ContextProviderDTO();
        first.setUrl("https://example.com/first");
        first.setHeaders(Map.of());
        ContextProviderDTO second = new ContextProviderDTO();
        second.setUrl("https://example.com/second");
        second.setHeaders(Map.of());
        AgentSnapshotDataDTO current = new AgentSnapshotDataDTO();
        current.setContextProviders(List.of(first, second));
        AgentSnapshotDataDTO reordered = new AgentSnapshotDataDTO();
        reordered.setContextProviders(List.of(second, first));

        List<String> changedFields = (List<String>) method.invoke(service, current, reordered);

        assertEquals(List.of(AgentSnapshotField.CONTEXT_PROVIDERS.getFieldName()), changedFields);
    }

    @Test
    void redactSnapshotDataMasksSensitiveFunctionAndHeaderValues() throws Exception {
        AgentSnapshotServiceImpl service = new AgentSnapshotServiceImpl(null, null, null, null, null, null, null, null,
                null, null);
        Method method = AgentSnapshotServiceImpl.class.getDeclaredMethod("redactSnapshotData",
                AgentSnapshotDataDTO.class);
        method.setAccessible(true);

        AgentSnapshotDataDTO data = buildExtendedSensitiveSnapshot();

        AgentSnapshotDataDTO redacted = (AgentSnapshotDataDTO) method.invoke(service, data);
        String json = JsonUtils.toJsonString(redacted);

        assertExtendedSecretsAbsent(json);
        assertTrue(json.contains("__SNAPSHOT_SECRET_REDACTED__"));
        assertTrue(json.contains("max_tokens"));
        assertTrue(json.contains("application/json"));
    }

    @Test
    void snapshotDetailMasksCookieProxyAuthorizationAndSessionHeaders() throws Exception {
        AgentSnapshotDao snapshotDao = mock(AgentSnapshotDao.class);
        AgentSnapshotServiceImpl service = new AgentSnapshotServiceImpl(snapshotDao, null, null, null, null, null, null,
                null, null, null);
        Method method = AgentSnapshotServiceImpl.class.getDeclaredMethod("toVO",
                AgentSnapshotEntity.class, boolean.class);
        method.setAccessible(true);

        AgentSnapshotEntity entity = snapshotEntity("snapshot-id", "agent-id", 4, buildExtendedSensitiveSnapshot());
        when(snapshotDao.selectNextSnapshot("agent-id", 4)).thenReturn(null);

        AgentSnapshotVO detail = (AgentSnapshotVO) method.invoke(service, entity, true);
        String json = JsonUtils.toJsonString(detail);

        assertExtendedSecretsAbsent(json);
        assertTrue(json.contains("__SNAPSHOT_SECRET_REDACTED__"));
        assertTrue(json.contains("application/json"));
    }

    @Test
    void snapshotDetailReturnsCurrentPreviewDataAndTokenFromTheSameServerRead() {
        AgentSnapshotDao snapshotDao = mock(AgentSnapshotDao.class);
        AgentDao agentDao = mock(AgentDao.class);
        AgentTagDao tagDao = mock(AgentTagDao.class);
        AgentContextProviderService contextProviderService = mock(AgentContextProviderService.class);
        CorrectWordFileService correctWordFileService = mock(CorrectWordFileService.class);
        AgentSnapshotServiceImpl service = new AgentSnapshotServiceImpl(snapshotDao, agentDao, tagDao, null, null,
                contextProviderService, null, null, null, correctWordFileService);
        ReflectionTestUtils.setField(service, "baseDao", snapshotDao);

        String agentId = "agent-id";
        String snapshotId = "snapshot-id";
        AgentInfoVO current = snapshotAgentInfo(agentId, 7L, "current", "current-summary");
        AgentPluginMapping mapping = new AgentPluginMapping();
        mapping.setPluginId("plugin");
        mapping.setParamInfo("{\"api_key\":\"live-secret\",\"visible\":\"kept\","
                + "\"webhookUrl\":\"https://hooks.slack.com/services/T111/B222/live-path-secret\"}");
        current.setFunctions(List.of(mapping));
        AgentEntity lockedAgent = new AgentEntity();
        lockedAgent.setId(agentId);
        when(agentDao.selectByIdForUpdate(agentId)).thenReturn(lockedAgent);
        when(snapshotDao.selectById(snapshotId))
                .thenReturn(snapshotEntity(snapshotId, agentId, 2, snapshotData("target", "target-summary")));
        when(snapshotDao.selectNextSnapshot(agentId, 2)).thenReturn(null);
        when(agentDao.selectAgentInfoById(agentId)).thenReturn(current);
        when(contextProviderService.getByAgentId(agentId)).thenReturn(null);
        when(correctWordFileService.getAgentCorrectWordFileIds(agentId)).thenReturn(List.of());
        when(tagDao.selectByAgentId(agentId)).thenReturn(List.of());

        AgentSnapshotVO detail = service.getSnapshot(agentId, snapshotId);

        assertNotNull(detail.getCurrentSnapshotData());
        assertEquals(64, detail.getCurrentStateToken().length());
        String currentJson = JsonUtils.toJsonString(detail.getCurrentSnapshotData());
        assertFalse(currentJson.contains("live-secret"));
        assertFalse(currentJson.contains("live-path-secret"));
        assertTrue(currentJson.contains("__SNAPSHOT_SECRET_REDACTED__"));
        assertTrue(currentJson.contains("kept"));
    }

    @Test
    void legacyRedactionMigrationCleansStructuredAndUrlSecretsWithoutDroppingUnknownFields() {
        AgentSnapshotDao snapshotDao = mock(AgentSnapshotDao.class);
        AgentSnapshotServiceImpl service = new AgentSnapshotServiceImpl(snapshotDao, null, null, null, null, null,
                null, null, null, null);
        AgentSnapshotEntity legacy = new AgentSnapshotEntity();
        legacy.setId("legacy-id");
        legacy.setRedactionVersion(1);
        legacy.setSnapshotData(JsonUtils.toJsonString(Map.of(
                "futureField", Map.of(
                        "kept", true,
                        "primaryEndpoint", "https://api.example.com/hooks/events/status",
                        "secondaryEndpoint", "https://api.example.com/webhooks/events/status",
                        "singleHookEndpoint", "https://api.example.com/hooks/events",
                        "statusEndpoint", "https://api.example.com/webhooks/status",
                        "webhook", "incoming/legacy-token",
                        "description", "incoming/token",
                        "outgoingWebhookUrl", "https://example.com/incoming/legacy-path-secret"),
                "functions", List.of(Map.of("paramInfo", Map.of(
                        "headers", List.of(Map.of("NAME", "Authorization", "VALUE", "Bearer legacy-secret")),
                        "Cookie", "legacy-cookie",
                        "protocolRelativeEndpoint",
                        "//legacy-relative-user:legacy-relative-pass@example.com/public/path",
                        "endpoint", "https://user:pass@example.com/hook?subscription-key=legacy-key"))))));
        when(snapshotDao.selectLegacyRedactionBatch(null, 100, 2)).thenReturn(List.of(legacy));
        when(snapshotDao.selectLegacyRedactionBatch("legacy-id", 100, 2)).thenReturn(List.of());
        when(snapshotDao.updateRedactedSnapshots(any(), eq(2))).thenReturn(1);

        long migrated = service.redactLegacySnapshots();

        verify(snapshotDao).updateRedactedSnapshots(
                argThat(snapshots -> snapshots.size() == 1 && "legacy-id".equals(snapshots.get(0).getId())), eq(2));
        assertEquals(1, migrated);
        assertFalse(legacy.getSnapshotData().contains("legacy-secret"));
        assertFalse(legacy.getSnapshotData().contains("legacy-cookie"));
        assertFalse(legacy.getSnapshotData().contains("legacy-key"));
        assertFalse(legacy.getSnapshotData().contains("user:pass"));
        assertFalse(legacy.getSnapshotData().contains("legacy-path-secret"));
        assertFalse(legacy.getSnapshotData().contains("legacy-relative-user"));
        assertFalse(legacy.getSnapshotData().contains("legacy-relative-pass"));
        assertFalse(legacy.getSnapshotData().contains("incoming/legacy-token"));
        assertTrue(legacy.getSnapshotData().contains("futureField"));
        assertTrue(legacy.getSnapshotData().contains("\"kept\":true"));
        assertTrue(legacy.getSnapshotData().contains("https://api.example.com/hooks/events/status"));
        assertTrue(legacy.getSnapshotData().contains("https://api.example.com/webhooks/events/status"));
        assertTrue(legacy.getSnapshotData().contains("https://api.example.com/hooks/events"));
        assertTrue(legacy.getSnapshotData().contains("https://api.example.com/webhooks/status"));
        assertTrue(legacy.getSnapshotData().contains("//__SNAPSHOT_SECRET_REDACTED__@example.com/public/path"));
        assertTrue(legacy.getSnapshotData().contains("incoming/__SNAPSHOT_SECRET_REDACTED__"));
        assertTrue(legacy.getSnapshotData().contains("incoming/token"));
        assertTrue(legacy.getSnapshotData().contains("__SNAPSHOT_SECRET_REDACTED__"));
    }

    @Test
    void preserveCurrentSensitiveValuesKeepsCurrentSecretsWhenRestoringSnapshot() throws Exception {
        AgentSnapshotServiceImpl service = new AgentSnapshotServiceImpl(null, null, null, null, null, null, null, null,
                null, null);
        Method method = AgentSnapshotServiceImpl.class.getDeclaredMethod("preserveCurrentSensitiveValues",
                AgentSnapshotDataDTO.class, AgentSnapshotDataDTO.class);
        method.setAccessible(true);

        AgentSnapshotDataDTO snapshot = buildSnapshot("old-key", "old-token", "old-value");
        AgentSnapshotDataDTO current = buildSnapshot("current-key", "current-token", "current-value");

        AgentSnapshotDataDTO restored = (AgentSnapshotDataDTO) method.invoke(service, snapshot, current);

        assertEquals("current-key", restored.getFunctions().get(0).getParamInfo().get("api_key"));
        assertEquals("old-value", restored.getFunctions().get(0).getParamInfo().get("description"));
        assertEquals("current-token", restored.getContextProviders().get(0).getHeaders().get("Authorization"));
    }

    @Test
    void redactSnapshotDataMasksStructuredHeadersAndUrlCredentials() throws Exception {
        AgentSnapshotServiceImpl service = new AgentSnapshotServiceImpl(null, null, null, null, null, null, null, null,
                null, null);
        Method method = AgentSnapshotServiceImpl.class.getDeclaredMethod("redactSnapshotData",
                AgentSnapshotDataDTO.class);
        method.setAccessible(true);

        Map<String, Object> params = new HashMap<>();
        params.put("headers", List.of(
                Map.of("key", "Authorization", "value", "Bearer structured-secret"),
                Map.of("name", "Cookie", "value", "cookie=structured-cookie")));
        params.put("callbackUrl",
                "https://function-user:function-pass@example.com/hook?access_token=function-token#function-fragment");
        params.put("endpoint",
                "https://example.com/signed?locale=zh-CN&X-Amz-Signature=endpoint-signature");
        params.put("transport",
                "https://example.com/transport?mode=push&key=transport-key");
        params.put("mirrors", List.of(
                "https://example.com/nested?locale=en&token=nested-token"));
        AgentSnapshotDataDTO data = new AgentSnapshotDataDTO();
        data.setFunctions(List.of(functionInfo("plugin", params)));
        ContextProviderDTO provider = new ContextProviderDTO();
        provider.setUrl("https://provider-user:provider-pass@example.com/context?token=provider-token#provider-fragment");
        provider.setHeaders(Map.of());
        data.setContextProviders(List.of(provider));

        AgentSnapshotDataDTO redacted = (AgentSnapshotDataDTO) method.invoke(service, data);
        String json = JsonUtils.toJsonString(redacted);

        for (String secret : List.of("structured-secret", "structured-cookie", "function-user", "function-pass",
                "function-token", "function-fragment", "provider-user", "provider-pass", "provider-token",
                "provider-fragment", "endpoint-signature", "transport-key", "nested-token")) {
            assertFalse(json.contains(secret), () -> "Sensitive value leaked: " + secret);
        }
        assertEquals("https://__SNAPSHOT_SECRET_REDACTED__@example.com/context"
                        + "?token=__SNAPSHOT_SECRET_REDACTED__#__SNAPSHOT_SECRET_REDACTED__",
                redacted.getContextProviders().get(0).getUrl());
        assertEquals("https://example.com/signed?locale=zh-CN&X-Amz-Signature=__SNAPSHOT_SECRET_REDACTED__",
                redacted.getFunctions().get(0).getParamInfo().get("endpoint"));
        assertEquals("https://example.com/transport?mode=push&key=__SNAPSHOT_SECRET_REDACTED__",
                redacted.getFunctions().get(0).getParamInfo().get("transport"));
        assertTrue(json.contains("__SNAPSHOT_SECRET_REDACTED__"));
    }

    @Test
    void capabilityUrlPathsAreRedactedPreciselyAndIdempotently() throws Exception {
        AgentSnapshotServiceImpl service = new AgentSnapshotServiceImpl(null, null, null, null, null, null, null, null,
                null, null);
        Method method = AgentSnapshotServiceImpl.class.getDeclaredMethod("redactSensitiveUrl",
                String.class, String.class);
        method.setAccessible(true);

        Map<String, String> cases = new LinkedHashMap<>();
        cases.put("https://hooks.slack.com/services/T111/B222/slack-secret",
                "https://hooks.slack.com/services/T111/B222/__SNAPSHOT_SECRET_REDACTED__");
        cases.put("https://discord.com/api/v10/webhooks/123456/discord-secret",
                "https://discord.com/api/v10/webhooks/123456/__SNAPSHOT_SECRET_REDACTED__");
        cases.put("https://api.telegram.org/bot123456:telegram-secret/sendMessage",
                "https://api.telegram.org/bot123456:__SNAPSHOT_SECRET_REDACTED__/sendMessage");
        cases.put("https://hooks.zapier.com/hooks/catch/987/generic-secret",
                "https://hooks.zapier.com/hooks/__SNAPSHOT_SECRET_REDACTED__");
        cases.put("/api/webhooks/relative-secret/continuation",
                "/api/webhooks/__SNAPSHOT_SECRET_REDACTED__");

        for (Map.Entry<String, String> entry : cases.entrySet()) {
            String redacted = (String) method.invoke(service, entry.getKey(), "endpoint");
            assertEquals(entry.getValue(), redacted);
            assertEquals(redacted, method.invoke(service, redacted, "endpoint"));
        }

        assertEquals("https://example.com/incoming/__SNAPSHOT_SECRET_REDACTED__",
                method.invoke(service, "https://example.com/incoming/key-secret", "outgoingWebhookUrl"));
        assertEquals("https://api.example.com/v1/users/123/preferences",
                method.invoke(service, "https://api.example.com/v1/users/123/preferences", "endpoint"));
        assertEquals("https://api.example.com/hooks/events/status",
                method.invoke(service, "https://api.example.com/hooks/events/status", "endpoint"));
        assertEquals("https://api.example.com/webhooks/events/status",
                method.invoke(service, "https://api.example.com/webhooks/events/status", "endpoint"));
        assertEquals("https://api.example.com/hooks/events",
                method.invoke(service, "https://api.example.com/hooks/events", "endpoint"));
        assertEquals("https://api.example.com/webhooks/status",
                method.invoke(service, "https://api.example.com/webhooks/status", "endpoint"));
        assertEquals("https://api.example.com/hooks/__SNAPSHOT_SECRET_REDACTED__",
                method.invoke(service, "https://api.example.com/hooks/access-token-value", "endpoint"));
        assertEquals("https://api.example.com/webhooks/__SNAPSHOT_SECRET_REDACTED__",
                method.invoke(service, "https://api.example.com/webhooks/aB3dE5fG7hI9jK1mN3pQ5rS7", "endpoint"));
        assertEquals("/api/v1/agents/42",
                method.invoke(service, "/api/v1/agents/42", "endpoint"));
        assertEquals("incoming/__SNAPSHOT_SECRET_REDACTED__",
                method.invoke(service, "incoming/token", "webhook"));
        assertEquals("incoming/token",
                method.invoke(service, "incoming/token", "description"));
    }

    @Test
    @SuppressWarnings("unchecked")
    void pathCapabilityRotationDoesNotChangeSnapshotStateButPublicIdentityDoes() throws Exception {
        AgentSnapshotServiceImpl service = new AgentSnapshotServiceImpl(null, null, null, null, null, null, null, null,
                null, null);
        Method changedMethod = AgentSnapshotServiceImpl.class.getDeclaredMethod("getChangedFields",
                AgentSnapshotDataDTO.class, AgentSnapshotDataDTO.class);
        changedMethod.setAccessible(true);

        AgentSnapshotDataDTO current = new AgentSnapshotDataDTO();
        current.setFunctions(List.of(functionInfo("plugin", Map.of(
                "webhookUrl", "https://hooks.slack.com/services/T111/B222/first-secret",
                "endpoint", "/api/webhooks/first-relative-secret/continuation"))));
        AgentSnapshotDataDTO rotated = new AgentSnapshotDataDTO();
        rotated.setFunctions(List.of(functionInfo("plugin", Map.of(
                "webhookUrl", "https://hooks.slack.com/services/T111/B222/second-secret",
                "endpoint", "/api/webhooks/second-relative-secret/continuation"))));
        AgentSnapshotDataDTO differentPublicIdentity = new AgentSnapshotDataDTO();
        differentPublicIdentity.setFunctions(List.of(functionInfo("plugin", Map.of(
                "webhookUrl", "https://hooks.slack.com/services/T111/B999/second-secret",
                "endpoint", "/api/webhooks/second-relative-secret/continuation"))));

        assertTrue(((List<String>) changedMethod.invoke(service, current, rotated)).isEmpty());
        assertEquals(currentStateToken(service, current), currentStateToken(service, rotated));
        assertEquals(List.of(AgentSnapshotField.FUNCTIONS.getFieldName()),
                changedMethod.invoke(service, current, differentPublicIdentity));
        assertFalse(currentStateToken(service, current).equals(currentStateToken(service, differentPublicIdentity)));
    }

    @Test
    @SuppressWarnings("unchecked")
    void nestedWebhookSemanticKeysPropagateAcrossRedactionComparisonAndRestore() throws Exception {
        AgentSnapshotServiceImpl service = new AgentSnapshotServiceImpl(null, null, null, null, null, null, null, null,
                null, null);
        Method redactMethod = AgentSnapshotServiceImpl.class.getDeclaredMethod("redactSnapshotData",
                AgentSnapshotDataDTO.class);
        redactMethod.setAccessible(true);
        Method changedMethod = AgentSnapshotServiceImpl.class.getDeclaredMethod("getChangedFields",
                AgentSnapshotDataDTO.class, AgentSnapshotDataDTO.class);
        changedMethod.setAccessible(true);
        Method preserveMethod = AgentSnapshotServiceImpl.class.getDeclaredMethod("preserveCurrentSensitiveValues",
                AgentSnapshotDataDTO.class, AgentSnapshotDataDTO.class);
        preserveMethod.setAccessible(true);
        Method containsMethod = AgentSnapshotServiceImpl.class.getDeclaredMethod("containsSensitiveMaterial",
                Object.class);
        containsMethod.setAccessible(true);

        List<Map<String, Object>> nestedCases = List.of(
                Map.of("webhookConfig", Map.of("value",
                        "https://capability.example.com/public/nested-secret-one")),
                Map.of("deliveryWebhook", Map.of("options", Map.of("target",
                        "https://capability.example.com/public/nested-secret-two"))),
                Map.of("config", Map.of("webhookUrl",
                        "https://capability.example.com/public/nested-secret-three")));
        for (Map<String, Object> params : nestedCases) {
            AgentSnapshotDataDTO candidate = new AgentSnapshotDataDTO();
            candidate.setFunctions(List.of(functionInfo("plugin", params)));
            AgentSnapshotDataDTO redacted = (AgentSnapshotDataDTO) redactMethod.invoke(service, candidate);
            String json = JsonUtils.toJsonString(redacted);
            for (String secret : List.of("nested-secret-one", "nested-secret-two", "nested-secret-three")) {
                assertFalse(json.contains(secret), () -> "Nested webhook capability leaked: " + secret);
            }
            assertTrue(json.contains("__SNAPSHOT_SECRET_REDACTED__"));
        }

        AgentSnapshotDataDTO first = nestedWebhookSnapshot("first-current-secret");
        AgentSnapshotDataDTO rotated = nestedWebhookSnapshot("rotated-current-secret");
        assertTrue(((List<String>) changedMethod.invoke(service, first, rotated)).isEmpty());
        assertEquals(currentStateToken(service, first), currentStateToken(service, rotated));

        AgentSnapshotDataDTO target = (AgentSnapshotDataDTO) redactMethod.invoke(service,
                nestedWebhookSnapshot("historical-secret"));
        AgentSnapshotDataDTO restored = (AgentSnapshotDataDTO) preserveMethod.invoke(service, target, rotated);
        Map<String, Object> webhookConfig = (Map<String, Object>) restored.getFunctions().get(0)
                .getParamInfo().get("webhookConfig");
        assertEquals("https://capability.example.com/public/rotated-current-secret", webhookConfig.get("value"));
        assertTrue((Boolean) containsMethod.invoke(service,
                target.getFunctions().get(0).getParamInfo()));
    }

    @Test
    void restoringPathCapabilitiesCopiesOnlyCurrentSecretAndRejectsUnsafeIdentity() throws Exception {
        AgentSnapshotServiceImpl service = new AgentSnapshotServiceImpl(null, null, null, null, null, null, null, null,
                null, null);
        Method redactMethod = AgentSnapshotServiceImpl.class.getDeclaredMethod("redactSensitiveUrl",
                String.class, String.class);
        redactMethod.setAccessible(true);
        Method preserveMethod = AgentSnapshotServiceImpl.class.getDeclaredMethod("preserveCurrentSensitiveUrl",
                String.class, String.class, String.class);
        preserveMethod.setAccessible(true);

        String target = (String) redactMethod.invoke(service,
                "https://hooks.slack.com/services/T111/B222/historical-secret", "webhookUrl");
        assertEquals("https://hooks.slack.com/services/T111/B222/current-secret",
                preserveMethod.invoke(service, target,
                        "https://hooks.slack.com/services/T111/B222/current-secret", "webhookUrl"));
        String relativeTarget = (String) redactMethod.invoke(service,
                "/api/webhooks/historical-secret/continuation", "endpoint");
        assertEquals("/api/webhooks/current-relative/callback",
                preserveMethod.invoke(service, relativeTarget,
                        "/api/webhooks/current-relative/callback", "endpoint"));
        String bareRelativeTarget = (String) redactMethod.invoke(service,
                "incoming/historical-token", "webhook");
        assertEquals("incoming/current-token",
                preserveMethod.invoke(service, bareRelativeTarget,
                        "incoming/current-token", "webhook"));

        InvocationTargetException mismatch = assertThrows(InvocationTargetException.class,
                () -> preserveMethod.invoke(service, target,
                        "https://hooks.slack.com/services/T111/B999/current-secret", "webhookUrl"));
        assertTrue(mismatch.getCause() instanceof RenException);
        InvocationTargetException missing = assertThrows(InvocationTargetException.class,
                () -> preserveMethod.invoke(service, target, null, "webhookUrl"));
        assertTrue(missing.getCause() instanceof RenException);
        InvocationTargetException placeholder = assertThrows(InvocationTargetException.class,
                () -> preserveMethod.invoke(service, target,
                        "https://hooks.slack.com/services/T111/B222/__SNAPSHOT_SECRET_REDACTED__", "webhookUrl"));
        assertTrue(placeholder.getCause() instanceof RenException);
        InvocationTargetException relativeMismatch = assertThrows(InvocationTargetException.class,
                () -> preserveMethod.invoke(service, relativeTarget,
                        "/different/webhooks/current-relative/callback", "endpoint"));
        assertTrue(relativeMismatch.getCause() instanceof RenException);
        InvocationTargetException bareRelativeMismatch = assertThrows(InvocationTargetException.class,
                () -> preserveMethod.invoke(service, bareRelativeTarget,
                        "outgoing/current-token", "webhook"));
        assertTrue(bareRelativeMismatch.getCause() instanceof RenException);
    }

    @Test
    void duplicatePublicPathIdentitiesAreRejectedInsteadOfGuessingASecret() throws Exception {
        AgentSnapshotServiceImpl service = new AgentSnapshotServiceImpl(null, null, null, null, null, null, null, null,
                null, null);
        Method redactMethod = AgentSnapshotServiceImpl.class.getDeclaredMethod("redactSnapshotData",
                AgentSnapshotDataDTO.class);
        redactMethod.setAccessible(true);
        Method preserveMethod = AgentSnapshotServiceImpl.class.getDeclaredMethod("preserveCurrentSensitiveValues",
                AgentSnapshotDataDTO.class, AgentSnapshotDataDTO.class);
        preserveMethod.setAccessible(true);

        AgentSnapshotDataDTO target = new AgentSnapshotDataDTO();
        target.setFunctions(List.of(functionInfo("plugin", Map.of("webhooks", List.of(
                "https://hooks.slack.com/services/T111/B222/historical-secret")))));
        target = (AgentSnapshotDataDTO) redactMethod.invoke(service, target);
        AgentSnapshotDataDTO current = new AgentSnapshotDataDTO();
        current.setFunctions(List.of(functionInfo("plugin", Map.of("webhooks", List.of(
                "https://hooks.slack.com/services/T111/B222/current-one",
                "https://hooks.slack.com/services/T111/B222/current-two")))));

        AgentSnapshotDataDTO redactedTarget = target;
        InvocationTargetException ambiguous = assertThrows(InvocationTargetException.class,
                () -> preserveMethod.invoke(service, redactedTarget, current));
        assertTrue(ambiguous.getCause() instanceof RenException);
    }

    @Test
    @SuppressWarnings("unchecked")
    void sensitiveListItemsWithoutNamedIdsUseUniquePublicFingerprint() throws Exception {
        AgentSnapshotServiceImpl service = new AgentSnapshotServiceImpl(null, null, null, null, null, null, null, null,
                null, null);
        Method redactMethod = AgentSnapshotServiceImpl.class.getDeclaredMethod("redactSnapshotData",
                AgentSnapshotDataDTO.class);
        redactMethod.setAccessible(true);
        Method preserveMethod = AgentSnapshotServiceImpl.class.getDeclaredMethod("preserveCurrentSensitiveValues",
                AgentSnapshotDataDTO.class, AgentSnapshotDataDTO.class);
        preserveMethod.setAccessible(true);

        AgentSnapshotDataDTO target = new AgentSnapshotDataDTO();
        target.setFunctions(List.of(functionInfo("plugin", Map.of("destinations", List.of(
                Map.of("host", "alpha.example.com", "api_key", "historical-secret"))))));
        target = (AgentSnapshotDataDTO) redactMethod.invoke(service, target);

        AgentSnapshotDataDTO current = new AgentSnapshotDataDTO();
        current.setFunctions(List.of(functionInfo("plugin", Map.of("destinations", List.of(
                Map.of("host", "alpha.example.com", "api_key", "current-secret"))))));
        AgentSnapshotDataDTO restored = (AgentSnapshotDataDTO) preserveMethod.invoke(service, target, current);
        List<Map<String, Object>> destinations = (List<Map<String, Object>>) restored.getFunctions().get(0)
                .getParamInfo().get("destinations");
        assertEquals("current-secret", destinations.get(0).get("api_key"));

        AgentSnapshotDataDTO ambiguousCurrent = new AgentSnapshotDataDTO();
        ambiguousCurrent.setFunctions(List.of(functionInfo("plugin", Map.of("destinations", List.of(
                Map.of("host", "alpha.example.com", "api_key", "first-current-secret"),
                Map.of("host", "alpha.example.com", "api_key", "second-current-secret"))))));
        AgentSnapshotDataDTO redactedTarget = target;
        InvocationTargetException ambiguous = assertThrows(InvocationTargetException.class,
                () -> preserveMethod.invoke(service, redactedTarget, ambiguousCurrent));
        assertTrue(ambiguous.getCause() instanceof RenException);
    }

    @Test
    void contextProvidersMatchPathCapabilitiesByUniquePublicIdentity() throws Exception {
        AgentSnapshotServiceImpl service = new AgentSnapshotServiceImpl(null, null, null, null, null, null, null, null,
                null, null);
        Method redactMethod = AgentSnapshotServiceImpl.class.getDeclaredMethod("redactSnapshotData",
                AgentSnapshotDataDTO.class);
        redactMethod.setAccessible(true);
        Method preserveMethod = AgentSnapshotServiceImpl.class.getDeclaredMethod("preserveCurrentSensitiveValues",
                AgentSnapshotDataDTO.class, AgentSnapshotDataDTO.class);
        preserveMethod.setAccessible(true);

        AgentSnapshotDataDTO target = new AgentSnapshotDataDTO();
        ContextProviderDTO targetProvider = new ContextProviderDTO();
        targetProvider.setUrl("https://discord.com/api/webhooks/123456/historical-secret");
        targetProvider.setHeaders(Map.of());
        target.setContextProviders(List.of(targetProvider));
        target = (AgentSnapshotDataDTO) redactMethod.invoke(service, target);

        AgentSnapshotDataDTO current = new AgentSnapshotDataDTO();
        ContextProviderDTO currentProvider = new ContextProviderDTO();
        currentProvider.setUrl("https://discord.com/api/webhooks/123456/current-secret");
        currentProvider.setHeaders(Map.of());
        current.setContextProviders(List.of(currentProvider));
        AgentSnapshotDataDTO restored = (AgentSnapshotDataDTO) preserveMethod.invoke(service, target, current);
        assertEquals("https://discord.com/api/webhooks/123456/current-secret",
                restored.getContextProviders().get(0).getUrl());

        currentProvider.setUrl("https://discord.com/api/webhooks/999999/current-secret");
        AgentSnapshotDataDTO redactedTarget = target;
        InvocationTargetException mismatch = assertThrows(InvocationTargetException.class,
                () -> preserveMethod.invoke(service, redactedTarget, current));
        assertTrue(mismatch.getCause() instanceof RenException);
    }

    @Test
    void snapshotPayloadReaderIgnoresFutureFieldsWithoutChangingGlobalJsonValidation() {
        AgentSnapshotServiceImpl service = new AgentSnapshotServiceImpl(null, null, null, null, null, null, null, null,
                null, null);
        String payload = "{\"agentName\":\"future-safe\",\"futureField\":{\"enabled\":true}}";

        AgentSnapshotDataDTO parsed = ReflectionTestUtils.invokeMethod(service, "parseSnapshotData", payload);

        assertNotNull(parsed);
        assertEquals("future-safe", parsed.getAgentName());
        assertThrows(RuntimeException.class, () -> JsonUtils.parseObject(payload, AgentSnapshotDataDTO.class));
    }

    @Test
    @SuppressWarnings("unchecked")
    void preserveSensitiveUrlListsByUrlIdentityInsteadOfIndex() throws Exception {
        AgentSnapshotServiceImpl service = new AgentSnapshotServiceImpl(null, null, null, null, null, null, null, null,
                null, null);
        Method redactMethod = AgentSnapshotServiceImpl.class.getDeclaredMethod("redactSnapshotData",
                AgentSnapshotDataDTO.class);
        redactMethod.setAccessible(true);
        Method preserveMethod = AgentSnapshotServiceImpl.class.getDeclaredMethod("preserveCurrentSensitiveValues",
                AgentSnapshotDataDTO.class, AgentSnapshotDataDTO.class);
        preserveMethod.setAccessible(true);

        AgentSnapshotDataDTO target = new AgentSnapshotDataDTO();
        target.setFunctions(List.of(functionInfo("plugin", Map.of("mirrors", List.of(
                "https://a.example.com/hook?token=old-a&locale=en",
                "https://b.example.com/hook?token=old-b&locale=en")))));
        target = (AgentSnapshotDataDTO) redactMethod.invoke(service, target);
        AgentSnapshotDataDTO current = new AgentSnapshotDataDTO();
        current.setFunctions(List.of(functionInfo("plugin", Map.of("mirrors", List.of(
                "https://b.example.com/hook?token=current-b&locale=de",
                "https://a.example.com/hook?token=current-a&locale=de")))));

        AgentSnapshotDataDTO restored = (AgentSnapshotDataDTO) preserveMethod.invoke(service, target, current);
        List<String> mirrors = (List<String>) restored.getFunctions().get(0).getParamInfo().get("mirrors");

        assertEquals(List.of(
                "https://a.example.com/hook?token=current-a&locale=en",
                "https://b.example.com/hook?token=current-b&locale=en"), mirrors);
    }

    @Test
    @SuppressWarnings("unchecked")
    void urlComparisonIgnoresOnlySensitiveParameterValues() throws Exception {
        AgentSnapshotServiceImpl service = new AgentSnapshotServiceImpl(null, null, null, null, null, null, null, null,
                null, null);
        Method method = AgentSnapshotServiceImpl.class.getDeclaredMethod("getChangedFields",
                AgentSnapshotDataDTO.class, AgentSnapshotDataDTO.class);
        method.setAccessible(true);

        AgentSnapshotDataDTO current = new AgentSnapshotDataDTO();
        current.setFunctions(List.of(functionInfo("plugin", Map.of("endpoint",
                "https://api.example.com/hook?locale=en&api_key=first&X-Amz-Signature=first-signature"))));
        AgentSnapshotDataDTO secretOnlyChange = new AgentSnapshotDataDTO();
        secretOnlyChange.setFunctions(List.of(functionInfo("plugin", Map.of("endpoint",
                "https://api.example.com/hook?locale=en&api_key=second&X-Amz-Signature=second-signature"))));
        AgentSnapshotDataDTO publicParameterChange = new AgentSnapshotDataDTO();
        publicParameterChange.setFunctions(List.of(functionInfo("plugin", Map.of("endpoint",
                "https://api.example.com/hook?locale=de&api_key=second&X-Amz-Signature=second-signature"))));

        assertTrue(((List<String>) method.invoke(service, current, secretOnlyChange)).isEmpty());
        assertEquals(List.of(AgentSnapshotField.FUNCTIONS.getFieldName()),
                method.invoke(service, current, publicParameterChange));
    }

    @Test
    @SuppressWarnings("unchecked")
    void preserveSensitiveHeaderListsByStableIdentityInsteadOfIndex() throws Exception {
        AgentSnapshotServiceImpl service = new AgentSnapshotServiceImpl(null, null, null, null, null, null, null, null,
                null, null);
        Method redactMethod = AgentSnapshotServiceImpl.class.getDeclaredMethod("redactSnapshotData",
                AgentSnapshotDataDTO.class);
        redactMethod.setAccessible(true);
        Method preserveMethod = AgentSnapshotServiceImpl.class.getDeclaredMethod("preserveCurrentSensitiveValues",
                AgentSnapshotDataDTO.class, AgentSnapshotDataDTO.class);
        preserveMethod.setAccessible(true);

        AgentSnapshotDataDTO target = new AgentSnapshotDataDTO();
        target.setFunctions(List.of(functionInfo("plugin", Map.of("headers", List.of(
                Map.of("key", "Authorization", "value", "old-auth"),
                Map.of("name", "Cookie", "value", "old-cookie"))))));
        target = (AgentSnapshotDataDTO) redactMethod.invoke(service, target);
        AgentSnapshotDataDTO current = new AgentSnapshotDataDTO();
        current.setFunctions(List.of(functionInfo("plugin", Map.of("headers", List.of(
                Map.of("name", "Cookie", "value", "current-cookie"),
                Map.of("key", "Authorization", "value", "current-auth"))))));

        AgentSnapshotDataDTO restored = (AgentSnapshotDataDTO) preserveMethod.invoke(service, target, current);
        List<Map<String, Object>> headers = (List<Map<String, Object>>) restored.getFunctions().get(0)
                .getParamInfo().get("headers");

        assertEquals("Authorization", headers.get(0).get("key"));
        assertEquals("current-auth", headers.get(0).get("value"));
        assertEquals("Cookie", headers.get(1).get("name"));
        assertEquals("current-cookie", headers.get(1).get("value"));
        assertFalse(JsonUtils.toJsonString(restored).contains("__SNAPSHOT_SECRET_REDACTED__"));
    }

    @Test
    @SuppressWarnings("unchecked")
    void structuredSensitiveValuesRequireOneEquivalentDiscriminator() throws Exception {
        AgentSnapshotServiceImpl service = new AgentSnapshotServiceImpl(null, null, null, null, null, null, null, null,
                null, null);
        Method redactMethod = AgentSnapshotServiceImpl.class.getDeclaredMethod("redactSensitiveMap", Map.class);
        redactMethod.setAccessible(true);
        Method preserveMethod = AgentSnapshotServiceImpl.class.getDeclaredMethod("preserveCurrentSensitiveMap",
                Map.class, Map.class);
        preserveMethod.setAccessible(true);

        Map<String, Object> target = (Map<String, Object>) redactMethod.invoke(service,
                Map.of("key", "Authorization", "value", "historical-secret"));
        Map<String, Object> restored = (Map<String, Object>) preserveMethod.invoke(service, target,
                Map.of("key", "authorization", "value", "current-secret"));
        assertEquals("current-secret", restored.get("value"));

        InvocationTargetException mismatchedType = assertThrows(InvocationTargetException.class,
                () -> preserveMethod.invoke(service, target,
                        Map.of("key", "Cookie", "value", "cookie-secret")));
        assertTrue(mismatchedType.getCause() instanceof RenException);

        Map<String, Object> ambiguousTarget = (Map<String, Object>) redactMethod.invoke(service,
                Map.of("key", "Authorization", "name", "Cookie", "value", "historical-secret"));
        InvocationTargetException ambiguous = assertThrows(InvocationTargetException.class,
                () -> preserveMethod.invoke(service, ambiguousTarget,
                        Map.of("key", "Authorization", "name", "Cookie", "value", "current-secret")));
        assertTrue(ambiguous.getCause() instanceof RenException);
    }

    @Test
    void restoringRedactedUrlsUsesTargetLocationAndCurrentCredentials() throws Exception {
        AgentSnapshotServiceImpl service = new AgentSnapshotServiceImpl(null, null, null, null, null, null, null, null,
                null, null);
        Method redactMethod = AgentSnapshotServiceImpl.class.getDeclaredMethod("redactSnapshotData",
                AgentSnapshotDataDTO.class);
        redactMethod.setAccessible(true);
        Method preserveMethod = AgentSnapshotServiceImpl.class.getDeclaredMethod("preserveCurrentSensitiveValues",
                AgentSnapshotDataDTO.class, AgentSnapshotDataDTO.class);
        preserveMethod.setAccessible(true);

        AgentSnapshotDataDTO target = new AgentSnapshotDataDTO();
        target.setFunctions(List.of(functionInfo("plugin", Map.of("callbackUrl",
                "https://old-user:old-pass@old.example.com/hook"
                        + "?api%5Fkey=old-token&locale=en#token=old-fragment&section=target"))));
        ContextProviderDTO targetProvider = new ContextProviderDTO();
        targetProvider.setUrl("https://old-user:old-pass@api.example.com/context"
                + "?api_key=old-token&locale=en#sig=old-fragment&section=target");
        targetProvider.setHeaders(Map.of());
        target.setContextProviders(List.of(targetProvider));
        target = (AgentSnapshotDataDTO) redactMethod.invoke(service, target);

        AgentSnapshotDataDTO current = new AgentSnapshotDataDTO();
        current.setFunctions(List.of(functionInfo("plugin", Map.of("callbackUrl",
                "https://current-user:current-pass@old.example.com/hook"
                        + "?api_key=current-token&locale=de#token=current-fragment&section=current"))));
        ContextProviderDTO currentProvider = new ContextProviderDTO();
        currentProvider.setUrl(
                "https://current-user:current-pass@api.example.com/context"
                        + "?api_key=current-token&locale=de#sig=current-fragment&section=current");
        currentProvider.setHeaders(Map.of());
        current.setContextProviders(List.of(currentProvider));

        AgentSnapshotDataDTO restored = (AgentSnapshotDataDTO) preserveMethod.invoke(service, target, current);

        assertEquals("https://current-user:current-pass@old.example.com/hook"
                        + "?api%5Fkey=current-token&locale=en#token=current-fragment&section=target",
                restored.getFunctions().get(0).getParamInfo().get("callbackUrl"));
        assertEquals("https://current-user:current-pass@api.example.com/context"
                        + "?api_key=current-token&locale=en#sig=current-fragment&section=target",
                restored.getContextProviders().get(0).getUrl());
        assertFalse(JsonUtils.toJsonString(restored).contains("__SNAPSHOT_SECRET_REDACTED__"));
    }

    @Test
    void urlSecretRestoreRequiresTheSamePublicSchemeAuthorityAndPath() throws Exception {
        AgentSnapshotServiceImpl service = new AgentSnapshotServiceImpl(null, null, null, null, null, null, null, null,
                null, null);
        Method redactMethod = AgentSnapshotServiceImpl.class.getDeclaredMethod("redactSensitiveUrl",
                String.class, String.class);
        redactMethod.setAccessible(true);
        Method preserveMethod = AgentSnapshotServiceImpl.class.getDeclaredMethod("preserveCurrentSensitiveUrl",
                String.class, String.class, String.class);
        preserveMethod.setAccessible(true);

        String target = (String) redactMethod.invoke(service,
                "https://old-user:old-pass@example.com/callback?token=old-token#old-fragment", "callbackUrl");
        assertEquals("https://new-user:new-pass@example.com/callback?token=current-token#current-fragment",
                preserveMethod.invoke(service, target,
                        "https://new-user:new-pass@example.com/callback?token=current-token#current-fragment",
                        "callbackUrl"));

        for (String mismatch : List.of(
                "https://new-user:new-pass@other.example.com/callback?token=current-token#current-fragment",
                "https://new-user:new-pass@example.com/other?token=current-token#current-fragment",
                "http://new-user:new-pass@example.com/callback?token=current-token#current-fragment")) {
            InvocationTargetException error = assertThrows(InvocationTargetException.class,
                    () -> preserveMethod.invoke(service, target, mismatch, "callbackUrl"));
            assertTrue(error.getCause() instanceof RenException);
        }
    }

    @Test
    void protocolRelativeUrlsRedactUserInfoAndRequireTheSamePublicBaseOnRestore() throws Exception {
        AgentSnapshotServiceImpl service = new AgentSnapshotServiceImpl(null, null, null, null, null, null, null, null,
                null, null);
        Method redactMethod = AgentSnapshotServiceImpl.class.getDeclaredMethod("redactSensitiveUrl",
                String.class, String.class);
        redactMethod.setAccessible(true);
        Method preserveMethod = AgentSnapshotServiceImpl.class.getDeclaredMethod("preserveCurrentSensitiveUrl",
                String.class, String.class, String.class);
        preserveMethod.setAccessible(true);

        String target = (String) redactMethod.invoke(service,
                "//old-user:old-pass@example.com/path?token=old-token", "endpoint");
        assertEquals("//__SNAPSHOT_SECRET_REDACTED__@example.com/path"
                + "?token=__SNAPSHOT_SECRET_REDACTED__", target);
        assertEquals("//current-user:current-pass@example.com/path?token=current-token",
                preserveMethod.invoke(service, target,
                        "//current-user:current-pass@example.com/path?token=current-token", "endpoint"));

        for (String mismatch : List.of(
                "//current-user:current-pass@other.example.com/path?token=current-token",
                "//current-user:current-pass@example.com/other?token=current-token",
                "https://current-user:current-pass@example.com/path?token=current-token")) {
            InvocationTargetException error = assertThrows(InvocationTargetException.class,
                    () -> preserveMethod.invoke(service, target, mismatch, "endpoint"));
            assertTrue(error.getCause() instanceof RenException);
        }
    }

    @Test
    @SuppressWarnings("unchecked")
    void restoringOlderStructureDetectsIrreversibleSensitiveRemovals() throws Exception {
        AgentSnapshotServiceImpl service = new AgentSnapshotServiceImpl(null, null, null, null, null, null, null, null,
                null, null);
        Method method = AgentSnapshotServiceImpl.class.getDeclaredMethod("preserveCurrentSensitiveValues",
                AgentSnapshotDataDTO.class, AgentSnapshotDataDTO.class);
        method.setAccessible(true);
        Method validateMethod = AgentSnapshotServiceImpl.class.getDeclaredMethod(
                "validateSensitiveRestoreIsReversible", AgentSnapshotDataDTO.class, AgentSnapshotDataDTO.class);
        validateMethod.setAccessible(true);

        AgentSnapshotDataDTO noPluginsTarget = new AgentSnapshotDataDTO();
        noPluginsTarget.setFunctions(List.of());
        AgentSnapshotDataDTO currentWithPlugin = new AgentSnapshotDataDTO();
        currentWithPlugin.setFunctions(List.of(functionInfo("new-plugin", Map.of("api_key", "current-secret"))));

        AgentSnapshotDataDTO removedPlugin = (AgentSnapshotDataDTO) method.invoke(service, noPluginsTarget,
                currentWithPlugin);
        assertTrue(removedPlugin.getFunctions().isEmpty());
        InvocationTargetException removedPluginError = assertThrows(InvocationTargetException.class,
                () -> validateMethod.invoke(service, currentWithPlugin, removedPlugin));
        assertTrue(removedPluginError.getCause() instanceof RenException);

        AgentSnapshotDataDTO headerTarget = new AgentSnapshotDataDTO();
        headerTarget.setFunctions(List.of(functionInfo("plugin", Map.of("headers", List.of(
                Map.of("key", "Content-Type", "value", "application/json"))))));
        AgentSnapshotDataDTO headerCurrent = new AgentSnapshotDataDTO();
        headerCurrent.setFunctions(List.of(functionInfo("plugin", Map.of("headers", List.of(
                Map.of("key", "Authorization", "value", "current-secret"),
                Map.of("key", "Content-Type", "value", "text/plain"))))));

        AgentSnapshotDataDTO removedHeader = (AgentSnapshotDataDTO) method.invoke(service, headerTarget,
                headerCurrent);
        List<Map<String, Object>> headers = (List<Map<String, Object>>) removedHeader.getFunctions().get(0)
                .getParamInfo().get("headers");
        assertEquals(1, headers.size());
        assertEquals("Content-Type", headers.get(0).get("key"));
        assertEquals("application/json", headers.get(0).get("value"));
        InvocationTargetException removedHeaderError = assertThrows(InvocationTargetException.class,
                () -> validateMethod.invoke(service, headerCurrent, removedHeader));
        assertTrue(removedHeaderError.getCause() instanceof RenException);

        AgentSnapshotDataDTO urlTarget = new AgentSnapshotDataDTO();
        urlTarget.setFunctions(List.of(functionInfo("plugin", Map.of("endpoint",
                "https://example.com/hook?locale=en"))));
        AgentSnapshotDataDTO urlCurrent = new AgentSnapshotDataDTO();
        urlCurrent.setFunctions(List.of(functionInfo("plugin", Map.of("endpoint",
                "https://example.com/hook?api_key=current-secret&locale=de"))));
        AgentSnapshotDataDTO removedUrlSecret = (AgentSnapshotDataDTO) method.invoke(service, urlTarget, urlCurrent);
        assertEquals("https://example.com/hook?locale=en",
                removedUrlSecret.getFunctions().get(0).getParamInfo().get("endpoint"));
        InvocationTargetException removedUrlError = assertThrows(InvocationTargetException.class,
                () -> validateMethod.invoke(service, urlCurrent, removedUrlSecret));
        assertTrue(removedUrlError.getCause() instanceof RenException);
    }

    @Test
    void ambiguousOrHistoricalRawSensitiveTargetsAreRejectedInsteadOfGuessed() throws Exception {
        AgentSnapshotServiceImpl service = new AgentSnapshotServiceImpl(null, null, null, null, null, null, null, null,
                null, null);
        Method method = AgentSnapshotServiceImpl.class.getDeclaredMethod("preserveCurrentSensitiveValues",
                AgentSnapshotDataDTO.class, AgentSnapshotDataDTO.class);
        method.setAccessible(true);

        AgentSnapshotDataDTO ambiguous = new AgentSnapshotDataDTO();
        ambiguous.setFunctions(List.of(functionInfo("plugin", Map.of("headers", List.of(
                Map.of("value", "__SNAPSHOT_SECRET_REDACTED__"))))));
        InvocationTargetException ambiguousError = assertThrows(InvocationTargetException.class,
                () -> method.invoke(service, ambiguous, new AgentSnapshotDataDTO()));
        assertTrue(ambiguousError.getCause() instanceof RenException);

        AgentSnapshotDataDTO conflictingIdentities = new AgentSnapshotDataDTO();
        conflictingIdentities.setFunctions(List.of(functionInfo("plugin", Map.of("headers", List.of(
                Map.of("name", "Shared", "key", "Authorization", "value",
                        "__SNAPSHOT_SECRET_REDACTED__"))))));
        AgentSnapshotDataDTO conflictingCurrent = new AgentSnapshotDataDTO();
        conflictingCurrent.setFunctions(List.of(functionInfo("plugin", Map.of("headers", List.of(
                Map.of("name", "Shared", "key", "Cookie", "value", "cookie-secret"),
                Map.of("name", "Different", "key", "Authorization", "value", "auth-secret"))))));
        InvocationTargetException conflictingError = assertThrows(InvocationTargetException.class,
                () -> method.invoke(service, conflictingIdentities, conflictingCurrent));
        assertTrue(conflictingError.getCause() instanceof RenException);

        AgentSnapshotDataDTO historicalRaw = new AgentSnapshotDataDTO();
        historicalRaw.setFunctions(List.of(functionInfo("plugin", Map.of("Authorization", "old-raw-secret"))));
        AgentSnapshotDataDTO current = new AgentSnapshotDataDTO();
        current.setFunctions(List.of(functionInfo("plugin", Map.of())));
        InvocationTargetException rawSecretError = assertThrows(InvocationTargetException.class,
                () -> method.invoke(service, historicalRaw, current));
        assertTrue(rawSecretError.getCause() instanceof RenException);

        AgentSnapshotDataDTO historicalRawUrl = new AgentSnapshotDataDTO();
        historicalRawUrl.setFunctions(List.of(functionInfo("plugin", Map.of("endpoint",
                "https://example.com/hook?api_key=historical-secret&locale=en"))));
        AgentSnapshotDataDTO currentUrlWithoutSecret = new AgentSnapshotDataDTO();
        currentUrlWithoutSecret.setFunctions(List.of(functionInfo("plugin", Map.of("endpoint",
                "https://example.com/hook?locale=de"))));
        InvocationTargetException rawUrlSecretError = assertThrows(InvocationTargetException.class,
                () -> method.invoke(service, historicalRawUrl, currentUrlWithoutSecret));
        assertTrue(rawUrlSecretError.getCause() instanceof RenException);
    }

    @Test
    @SuppressWarnings("unchecked")
    void getChangedFieldsFollowsCentralFieldOrder() throws Exception {
        AgentSnapshotServiceImpl service = new AgentSnapshotServiceImpl(null, null, null, null, null, null, null, null,
                null, null);
        Method method = AgentSnapshotServiceImpl.class.getDeclaredMethod("getChangedFields",
                AgentSnapshotDataDTO.class, AgentUpdateDTO.class);
        method.setAccessible(true);

        AgentSnapshotDataDTO current = new AgentSnapshotDataDTO();
        current.setAgentName("old-name");
        current.setCorrectWordFileIds(List.of("b", "a"));

        AgentUpdateDTO pendingUpdate = new AgentUpdateDTO();
        pendingUpdate.setAgentName("new-name");
        pendingUpdate.setCorrectWordFileIds(List.of("a", "b"));
        AgentUpdateDTO.FunctionInfo function = new AgentUpdateDTO.FunctionInfo();
        function.setPluginId("rag");
        function.setParamInfo(Map.of("api_key", "secret-key"));
        pendingUpdate.setFunctions(List.of(function));

        List<String> changedFields = (List<String>) method.invoke(service, current, pendingUpdate);

        assertEquals(List.of(AgentSnapshotField.AGENT_NAME.getFieldName(),
                AgentSnapshotField.FUNCTIONS.getFieldName()), changedFields);
    }

    @Test
    @SuppressWarnings("unchecked")
    void tagIdsAreNotExposedAsIndependentSnapshotFields() throws Exception {
        AgentSnapshotServiceImpl service = new AgentSnapshotServiceImpl(null, null, null, null, null, null, null, null,
                null, null);
        Method method = AgentSnapshotServiceImpl.class.getDeclaredMethod("getChangedFields",
                AgentSnapshotDataDTO.class, AgentUpdateDTO.class);
        method.setAccessible(true);

        AgentSnapshotDataDTO current = new AgentSnapshotDataDTO();
        current.setTagNames(List.of("alpha", "beta"));

        AgentUpdateDTO pendingUpdate = new AgentUpdateDTO();
        pendingUpdate.setTagNames(List.of("beta", "alpha"));
        pendingUpdate.setTagIds(List.of("new-id"));

        List<String> changedFields = (List<String>) method.invoke(service, current, pendingUpdate);

        assertFalse(AgentSnapshotField.names().contains("tagIds"));
        assertFalse(changedFields.contains("tagIds"));
        assertTrue(changedFields.isEmpty());

        pendingUpdate.setTagNames(List.of("alpha", "gamma"));
        changedFields = (List<String>) method.invoke(service, current, pendingUpdate);

        assertEquals(List.of(AgentSnapshotField.TAG_NAMES.getFieldName()), changedFields);
    }

    @Test
    @SuppressWarnings("unchecked")
    void blankSummaryMemoryValuesAreNotSnapshotChanges() throws Exception {
        AgentSnapshotServiceImpl service = new AgentSnapshotServiceImpl(null, null, null, null, null, null, null, null,
                null, null);
        Method method = AgentSnapshotServiceImpl.class.getDeclaredMethod("getChangedFields",
                AgentSnapshotDataDTO.class, AgentSnapshotDataDTO.class);
        method.setAccessible(true);

        AgentSnapshotDataDTO current = new AgentSnapshotDataDTO();
        current.setSummaryMemory(null);
        AgentSnapshotDataDTO next = new AgentSnapshotDataDTO();
        next.setSummaryMemory("");

        List<String> changedFields = (List<String>) method.invoke(service, current, next);

        assertFalse(changedFields.contains(AgentSnapshotField.SUMMARY_MEMORY.getFieldName()));
        assertTrue(changedFields.isEmpty());
    }

    @Test
    @SuppressWarnings("unchecked")
    void nullTtsAdvancedValuesDifferFromExplicitZero() throws Exception {
        AgentSnapshotServiceImpl service = new AgentSnapshotServiceImpl(null, null, null, null, null, null, null, null,
                null, null);
        Method method = AgentSnapshotServiceImpl.class.getDeclaredMethod("getChangedFields",
                AgentSnapshotDataDTO.class, AgentSnapshotDataDTO.class);
        method.setAccessible(true);

        AgentSnapshotDataDTO current = new AgentSnapshotDataDTO();
        current.setTtsVolume(null);
        current.setTtsRate(null);
        current.setTtsPitch(null);
        AgentSnapshotDataDTO next = new AgentSnapshotDataDTO();
        next.setTtsVolume(0);
        next.setTtsRate(0);
        next.setTtsPitch(0);

        List<String> changedFields = (List<String>) method.invoke(service, current, next);

        assertEquals(List.of(
                AgentSnapshotField.TTS_VOLUME.getFieldName(),
                AgentSnapshotField.TTS_RATE.getFieldName(),
                AgentSnapshotField.TTS_PITCH.getFieldName()), changedFields);
    }

    @Test
    @SuppressWarnings("unchecked")
    void redactedSecretsDoNotCreateFalseSnapshotChangeButNonSensitiveValuesDo() throws Exception {
        AgentSnapshotServiceImpl service = new AgentSnapshotServiceImpl(null, null, null, null, null, null, null, null,
                null, null);
        Method method = AgentSnapshotServiceImpl.class.getDeclaredMethod("getChangedFields",
                AgentSnapshotDataDTO.class, AgentSnapshotDataDTO.class);
        method.setAccessible(true);

        AgentSnapshotDataDTO stored = buildSnapshot(
                "__SNAPSHOT_SECRET_REDACTED__", "__SNAPSHOT_SECRET_REDACTED__", "same-value");
        AgentSnapshotDataDTO current = buildSnapshot("current-key", "current-token", "same-value");

        List<String> changedFields = (List<String>) method.invoke(service, stored, current);

        assertTrue(changedFields.isEmpty());

        current.getFunctions().get(0).getParamInfo().put("description", "changed-value");
        changedFields = (List<String>) method.invoke(service, stored, current);

        assertEquals(List.of(AgentSnapshotField.FUNCTIONS.getFieldName()), changedFields);
    }

    @Test
    @SuppressWarnings("unchecked")
    void explicitTtsLanguageIsStoredAsSnapshotChangeEvenWhenItMatchesVoiceDefault() throws Exception {
        AgentSnapshotServiceImpl service = new AgentSnapshotServiceImpl(null, null, null, null, null, null, null, null,
                null, null);
        Method method = AgentSnapshotServiceImpl.class.getDeclaredMethod("getChangedFields",
                AgentSnapshotDataDTO.class, AgentSnapshotDataDTO.class);
        method.setAccessible(true);

        AgentSnapshotDataDTO current = new AgentSnapshotDataDTO();
        current.setTtsVoiceId("voice-id");
        current.setTtsLanguage(null);
        AgentSnapshotDataDTO next = new AgentSnapshotDataDTO();
        next.setTtsVoiceId("voice-id");
        next.setTtsLanguage("普通话");

        List<String> changedFields = (List<String>) method.invoke(service, current, next);

        assertEquals(List.of(AgentSnapshotField.TTS_LANGUAGE.getFieldName()), changedFields);
    }

    @Test
    void tagOnlySavePathCreatesSnapshot() throws Exception {
        String controller = Files.readString(Path.of("src/main/java/xiaozhi/modules/agent/controller/AgentController.java"));
        String roleConfig = Files.readString(Path.of("../manager-web/src/views/roleConfig.vue"));

        assertTrue(controller.contains("agentService.updateAgentById(id, dto);"));
        assertFalse(controller.contains("agentService.updateAgentById(id, dto, false);"));
        assertTrue(roleConfig.contains("configData.tagNames = tagNames;"));
        assertFalse(roleConfig.contains("this.handleSaveAgentTags(agentId, tagNames)"));
    }

    @Test
    void firstAgentSaveKeepsInitialBaselineBeforePersistingNewState() {
        AgentDao agentDao = mock(AgentDao.class);
        AgentContextProviderService contextProviderService = mock(AgentContextProviderService.class);
        CorrectWordFileService correctWordFileService = mock(CorrectWordFileService.class);
        AgentSnapshotService snapshotService = mock(AgentSnapshotService.class);
        AgentServiceImpl service = new AgentServiceImpl(agentDao, null, null, null, null, null, null, null,
                null, null, contextProviderService, null, correctWordFileService, snapshotService);
        ReflectionTestUtils.setField(service, "baseDao", agentDao);

        String agentId = "agent-id";
        AgentEntity lockedAgent = new AgentEntity();
        lockedAgent.setId(agentId);
        AgentInfoVO currentAgent = new AgentInfoVO();
        currentAgent.setId(agentId);
        currentAgent.setAgentName("old-name");
        AgentUpdateDTO update = new AgentUpdateDTO();
        update.setAgentName("new-name");

        when(agentDao.selectByIdForUpdate(agentId)).thenReturn(lockedAgent);
        when(agentDao.selectAgentInfoById(agentId)).thenReturn(currentAgent);
        when(snapshotService.getCurrentVersionNo(agentId)).thenReturn(0);
        when(contextProviderService.getByAgentId(agentId)).thenReturn(null);
        when(correctWordFileService.getAgentCorrectWordFileIds(agentId)).thenReturn(List.of());
        when(agentDao.updateById(any(AgentEntity.class))).thenReturn(1);

        service.updateAgentById(agentId, update);

        InOrder inOrder = inOrder(agentDao, snapshotService);
        inOrder.verify(snapshotService).createSnapshot(agentId, "initial");
        inOrder.verify(agentDao).updateById(argThat((AgentEntity agent) -> "new-name".equals(agent.getAgentName())));
        inOrder.verify(snapshotService).createSnapshot(agentId, "config");
    }

    @Test
    void subsequentAgentSaveCapturesUnversionedCurrentStateBeforePersistingNewState() {
        AgentDao agentDao = mock(AgentDao.class);
        AgentContextProviderService contextProviderService = mock(AgentContextProviderService.class);
        CorrectWordFileService correctWordFileService = mock(CorrectWordFileService.class);
        AgentSnapshotService snapshotService = mock(AgentSnapshotService.class);
        AgentServiceImpl service = new AgentServiceImpl(agentDao, null, null, null, null, null, null, null,
                null, null, contextProviderService, null, correctWordFileService, snapshotService);
        ReflectionTestUtils.setField(service, "baseDao", agentDao);

        String agentId = "agent-id";
        AgentEntity lockedAgent = new AgentEntity();
        lockedAgent.setId(agentId);
        AgentInfoVO currentAgent = new AgentInfoVO();
        currentAgent.setId(agentId);
        currentAgent.setAgentName("old-name");
        AgentUpdateDTO update = new AgentUpdateDTO();
        update.setAgentName("new-name");

        when(agentDao.selectByIdForUpdate(agentId)).thenReturn(lockedAgent);
        when(agentDao.selectAgentInfoById(agentId)).thenReturn(currentAgent);
        when(snapshotService.getCurrentVersionNo(agentId)).thenReturn(4);
        when(contextProviderService.getByAgentId(agentId)).thenReturn(null);
        when(correctWordFileService.getAgentCorrectWordFileIds(agentId)).thenReturn(List.of());
        when(agentDao.updateById(any(AgentEntity.class))).thenReturn(1);

        service.updateAgentById(agentId, update);

        InOrder inOrder = inOrder(agentDao, snapshotService);
        inOrder.verify(snapshotService).createSnapshot(agentId, "current");
        inOrder.verify(agentDao).updateById(argThat((AgentEntity agent) -> "new-name".equals(agent.getAgentName())));
        inOrder.verify(snapshotService).createSnapshot(agentId, "config");
    }

    @Test
    void createAgentPersistsDisplayDefaultsBeforeInitialSnapshot() {
        AgentDao agentDao = mock(AgentDao.class);
        TimbreService timbreService = mock(TimbreService.class);
        AgentPluginMappingService pluginMappingService = mock(AgentPluginMappingService.class);
        AgentTemplateService templateService = mock(AgentTemplateService.class);
        ModelProviderService providerService = mock(ModelProviderService.class);
        AgentSnapshotService snapshotService = mock(AgentSnapshotService.class);
        AgentServiceImpl service = new AgentServiceImpl(agentDao, null, timbreService, null, null, null,
                pluginMappingService, null, templateService, providerService, null, null, null, snapshotService);
        ReflectionTestUtils.setField(service, "baseDao", agentDao);

        AgentTemplateEntity template = new AgentTemplateEntity();
        template.setTtsModelId("TTS_EdgeTTS");
        template.setTtsVoiceId("TTS_EdgeTTS0001");
        template.setMemModelId("Memory_nomem");
        template.setSummaryMemory(null);
        when(templateService.getDefaultTemplate()).thenReturn(template);

        when(timbreService.getDefaultLanguageById("TTS_EdgeTTS0001")).thenReturn("普通话");
        when(agentDao.insert(any(AgentEntity.class))).thenReturn(1);

        AgentCreateDTO dto = new AgentCreateDTO();
        dto.setAgentName("test123");

        String agentId = service.createAgent(dto);

        InOrder inOrder = inOrder(agentDao, pluginMappingService, snapshotService);
        inOrder.verify(agentDao).insert(argThat((AgentEntity agent) -> "test123".equals(agent.getAgentName())
                && "普通话".equals(agent.getTtsLanguage())
                && "".equals(agent.getSummaryMemory())
                && Integer.valueOf(0).equals(agent.getChatHistoryConf())));
        inOrder.verify(pluginMappingService).saveBatch(any(), eq(IRepository.DEFAULT_BATCH_SIZE));
        inOrder.verify(snapshotService).createSnapshot(agentId, "initial");
    }

    @Test
    void agentSnapshotFieldAppliesRestorableAgentFields() {
        AgentSnapshotDataDTO data = new AgentSnapshotDataDTO();
        data.setAgentName("restored-name");
        data.setLlmModelId("llm-new");
        data.setSystemPrompt("restored prompt");
        data.setSort(7);

        AgentEntity agent = new AgentEntity();
        for (AgentSnapshotField field : AgentSnapshotField.values()) {
            field.applyTo(agent, data);
        }

        assertEquals("restored-name", agent.getAgentName());
        assertEquals("llm-new", agent.getLlmModelId());
        assertEquals("restored prompt", agent.getSystemPrompt());
        assertEquals(7, agent.getSort());
    }

    @Test
    void restoreSnapshotRollsBackForAnyException() throws Exception {
        Method method = AgentSnapshotServiceImpl.class.getMethod("restoreSnapshot", String.class, String.class,
                String.class);

        Transactional transactional = method.getAnnotation(Transactional.class);

        assertNotNull(transactional);
        assertTrue(List.of(transactional.rollbackFor()).contains(Exception.class));
    }

    @Test
    void restoreSnapshotRejectsStalePreviewTokenBeforeAnyMutation() {
        AgentSnapshotDao snapshotDao = mock(AgentSnapshotDao.class);
        AgentDao agentDao = mock(AgentDao.class);
        AgentTagDao tagDao = mock(AgentTagDao.class);
        AgentPluginMappingService pluginMappingService = mock(AgentPluginMappingService.class);
        AgentContextProviderService contextProviderService = mock(AgentContextProviderService.class);
        CorrectWordFileService correctWordFileService = mock(CorrectWordFileService.class);
        AgentSnapshotServiceImpl service = new AgentSnapshotServiceImpl(snapshotDao, agentDao, tagDao, null,
                pluginMappingService, contextProviderService, null, null, null, correctWordFileService);
        ReflectionTestUtils.setField(service, "baseDao", snapshotDao);

        String agentId = "agent-id";
        String targetId = "target-id";
        AgentEntity lockedAgent = new AgentEntity();
        lockedAgent.setId(agentId);
        when(agentDao.selectByIdForUpdate(agentId)).thenReturn(lockedAgent);
        when(snapshotDao.selectById(targetId))
                .thenReturn(snapshotEntity(targetId, agentId, 2, snapshotData("target", "target-summary")));
        when(agentDao.selectAgentInfoById(agentId))
                .thenReturn(snapshotAgentInfo(agentId, 7L, "changed-after-preview", "live-summary"));
        when(contextProviderService.getByAgentId(agentId)).thenReturn(null);
        when(correctWordFileService.getAgentCorrectWordFileIds(agentId)).thenReturn(List.of());
        when(tagDao.selectByAgentId(agentId)).thenReturn(List.of());

        RenException error = assertThrows(RenException.class,
                () -> service.restoreSnapshot(agentId, targetId, "stale-token"));

        assertTrue(error.getMessage().contains("重新打开恢复预览"));
        verify(snapshotDao, never()).selectLatestSnapshot(agentId);
        verify(snapshotDao, never()).insertWithNextVersion(any());
        verify(agentDao, never()).updateSnapshotFields(any());
        verify(pluginMappingService, never()).deleteByAgentId(any());
    }

    @Test
    void restoreSnapshotBacksUpUnversionedMemoryThenStoresAppliedStateAsLatest() {
        AgentSnapshotDao snapshotDao = mock(AgentSnapshotDao.class);
        AgentDao agentDao = mock(AgentDao.class);
        AgentTagDao tagDao = mock(AgentTagDao.class);
        AgentTagRelationDao tagRelationDao = mock(AgentTagRelationDao.class);
        AgentPluginMappingService pluginMappingService = mock(AgentPluginMappingService.class);
        AgentContextProviderService contextProviderService = mock(AgentContextProviderService.class);
        AgentTagService tagService = mock(AgentTagService.class);
        AgentChatHistoryService chatHistoryService = mock(AgentChatHistoryService.class);
        CorrectWordFileService correctWordFileService = mock(CorrectWordFileService.class);
        AgentSnapshotServiceImpl service = new AgentSnapshotServiceImpl(snapshotDao, agentDao, tagDao, tagRelationDao,
                pluginMappingService, contextProviderService, tagService, chatHistoryService, null,
                correctWordFileService);
        ReflectionTestUtils.setField(service, "baseDao", snapshotDao);

        String agentId = "agent-id";
        String targetId = "target-id";
        AgentEntity lockedAgent = new AgentEntity();
        lockedAgent.setId(agentId);
        lockedAgent.setUserId(7L);
        AgentInfoVO currentInfo = snapshotAgentInfo(agentId, 7L, "current-name", "live-summary");
        AgentInfoVO restoredInfo = snapshotAgentInfo(agentId, 7L, "target-name", "target-summary");
        AgentSnapshotDataDTO currentData = snapshotData("current-name", "live-summary");
        AgentSnapshotDataDTO latestData = snapshotData("current-name", "snapshot-summary");
        AgentSnapshotDataDTO targetData = snapshotData("target-name", "target-summary");
        AgentSnapshotEntity target = snapshotEntity(targetId, agentId, 2, targetData);
        AgentSnapshotEntity latest = snapshotEntity("latest-id", agentId, 5, latestData);

        when(agentDao.selectByIdForUpdate(agentId)).thenReturn(lockedAgent);
        when(snapshotDao.selectById(targetId)).thenReturn(target);
        when(agentDao.selectAgentInfoById(agentId)).thenReturn(currentInfo, restoredInfo);
        when(snapshotDao.selectLatestSnapshot(agentId)).thenReturn(latest);
        when(contextProviderService.getByAgentId(agentId)).thenReturn(null);
        when(correctWordFileService.getAgentCorrectWordFileIds(agentId)).thenReturn(List.of());
        when(tagDao.selectByAgentId(agentId)).thenReturn(List.of());
        when(agentDao.updateSnapshotFields(any())).thenReturn(1);
        when(snapshotDao.insertWithNextVersion(any())).thenReturn(1);

        service.restoreSnapshot(agentId, targetId, currentStateToken(service, currentData));

        ArgumentCaptor<AgentSnapshotEntity> snapshotCaptor = ArgumentCaptor.forClass(AgentSnapshotEntity.class);
        verify(snapshotDao, org.mockito.Mockito.times(2)).insertWithNextVersion(snapshotCaptor.capture());
        List<AgentSnapshotEntity> inserted = snapshotCaptor.getAllValues();
        AgentSnapshotEntity backup = inserted.get(0);
        AgentSnapshotEntity restored = inserted.get(1);

        assertEquals("current", backup.getSource());
        assertNull(backup.getRestoreFromSnapshotId());
        assertNull(backup.getRestoreFromVersionNo());
        assertEquals(List.of(AgentSnapshotField.SUMMARY_MEMORY.getFieldName()),
                JsonUtils.parseObject(backup.getChangedFields(), new TypeReference<List<String>>() {
                }));
        assertEquals("live-summary",
                JsonUtils.parseObject(backup.getSnapshotData(), AgentSnapshotDataDTO.class).getSummaryMemory());

        assertEquals("restore", restored.getSource());
        assertEquals(targetId, restored.getRestoreFromSnapshotId());
        assertEquals(2, restored.getRestoreFromVersionNo());
        assertEquals("target-name",
                JsonUtils.parseObject(restored.getSnapshotData(), AgentSnapshotDataDTO.class).getAgentName());
        assertEquals("target-summary",
                JsonUtils.parseObject(restored.getSnapshotData(), AgentSnapshotDataDTO.class).getSummaryMemory());

        InOrder order = inOrder(snapshotDao, agentDao);
        order.verify(snapshotDao).insertWithNextVersion(backup);
        order.verify(agentDao).updateSnapshotFields(lockedAgent);
        order.verify(snapshotDao).insertWithNextVersion(restored);
        verify(snapshotDao).deleteOlderThanKeepLimit(agentId, 100);
    }

    @Test
    void restoreSnapshotSkipsBackupWhenLatestAlreadyRepresentsCurrentState() {
        AgentSnapshotDao snapshotDao = mock(AgentSnapshotDao.class);
        AgentDao agentDao = mock(AgentDao.class);
        AgentTagDao tagDao = mock(AgentTagDao.class);
        AgentPluginMappingService pluginMappingService = mock(AgentPluginMappingService.class);
        AgentContextProviderService contextProviderService = mock(AgentContextProviderService.class);
        AgentTagService tagService = mock(AgentTagService.class);
        CorrectWordFileService correctWordFileService = mock(CorrectWordFileService.class);
        AgentSnapshotServiceImpl service = new AgentSnapshotServiceImpl(snapshotDao, agentDao, tagDao, null,
                pluginMappingService, contextProviderService, tagService, null, null, correctWordFileService);
        ReflectionTestUtils.setField(service, "baseDao", snapshotDao);

        String agentId = "agent-id";
        String targetId = "target-id";
        AgentEntity lockedAgent = new AgentEntity();
        lockedAgent.setId(agentId);
        AgentInfoVO currentInfo = snapshotAgentInfo(agentId, 7L, "current-name", "current-summary");
        AgentInfoVO restoredInfo = snapshotAgentInfo(agentId, 7L, "target-name", "target-summary");
        AgentSnapshotDataDTO currentData = snapshotData("current-name", "current-summary");
        AgentSnapshotEntity target = snapshotEntity(targetId, agentId, 2,
                snapshotData("target-name", "target-summary"));

        when(agentDao.selectByIdForUpdate(agentId)).thenReturn(lockedAgent);
        when(snapshotDao.selectById(targetId)).thenReturn(target);
        when(agentDao.selectAgentInfoById(agentId)).thenReturn(currentInfo, restoredInfo);
        when(snapshotDao.selectLatestSnapshot(agentId)).thenReturn(snapshotEntity("latest-id", agentId, 5, currentData));
        when(contextProviderService.getByAgentId(agentId)).thenReturn(null);
        when(correctWordFileService.getAgentCorrectWordFileIds(agentId)).thenReturn(List.of());
        when(tagDao.selectByAgentId(agentId)).thenReturn(List.of());
        when(agentDao.updateSnapshotFields(any())).thenReturn(1);
        when(snapshotDao.insertWithNextVersion(any())).thenReturn(1);

        service.restoreSnapshot(agentId, targetId, currentStateToken(service, currentData));

        ArgumentCaptor<AgentSnapshotEntity> snapshotCaptor = ArgumentCaptor.forClass(AgentSnapshotEntity.class);
        verify(snapshotDao).insertWithNextVersion(snapshotCaptor.capture());
        assertEquals("restore", snapshotCaptor.getValue().getSource());
        assertEquals(targetId, snapshotCaptor.getValue().getRestoreFromSnapshotId());
        verify(snapshotDao).deleteOlderThanKeepLimit(agentId, 100);
    }

    @Test
    void restoreSnapshotContinuesWhenRelationOnlyChangeReportsZeroUpdatedAgentRows() {
        AgentSnapshotDao snapshotDao = mock(AgentSnapshotDao.class);
        AgentDao agentDao = mock(AgentDao.class);
        AgentTagDao tagDao = mock(AgentTagDao.class);
        AgentPluginMappingService pluginMappingService = mock(AgentPluginMappingService.class);
        AgentContextProviderService contextProviderService = mock(AgentContextProviderService.class);
        AgentTagService tagService = mock(AgentTagService.class);
        CorrectWordFileService correctWordFileService = mock(CorrectWordFileService.class);
        AgentSnapshotServiceImpl service = new AgentSnapshotServiceImpl(snapshotDao, agentDao, tagDao, null,
                pluginMappingService, contextProviderService, tagService, null, null, correctWordFileService);
        ReflectionTestUtils.setField(service, "baseDao", snapshotDao);

        String agentId = "agent-id";
        String targetId = "target-id";
        AgentEntity lockedAgent = new AgentEntity();
        lockedAgent.setId(agentId);
        lockedAgent.setUserId(7L);
        AgentInfoVO currentInfo = snapshotAgentInfo(agentId, 7L, "same-name", "same-summary");
        AgentInfoVO restoredInfo = snapshotAgentInfo(agentId, 7L, "same-name", "same-summary");
        AgentPluginMapping currentMapping = new AgentPluginMapping();
        currentMapping.setPluginId("plugin");
        currentMapping.setParamInfo("{\"description\":\"current\"}");
        currentInfo.setFunctions(List.of(currentMapping));
        AgentPluginMapping restoredMapping = new AgentPluginMapping();
        restoredMapping.setPluginId("plugin");
        restoredMapping.setParamInfo("{\"description\":\"target\"}");
        restoredInfo.setFunctions(List.of(restoredMapping));

        AgentSnapshotDataDTO currentData = snapshotData("same-name", "same-summary");
        currentData.setFunctions(List.of(functionInfo("plugin", Map.of("description", "current"))));
        AgentSnapshotDataDTO targetData = snapshotData("same-name", "same-summary");
        targetData.setFunctions(List.of(functionInfo("plugin", Map.of("description", "target"))));

        when(agentDao.selectByIdForUpdate(agentId)).thenReturn(lockedAgent);
        when(snapshotDao.selectById(targetId)).thenReturn(snapshotEntity(targetId, agentId, 2, targetData));
        when(agentDao.selectAgentInfoById(agentId)).thenReturn(currentInfo, restoredInfo);
        when(snapshotDao.selectLatestSnapshot(agentId))
                .thenReturn(snapshotEntity("latest-id", agentId, 5, currentData));
        when(contextProviderService.getByAgentId(agentId)).thenReturn(null);
        when(correctWordFileService.getAgentCorrectWordFileIds(agentId)).thenReturn(List.of());
        when(tagDao.selectByAgentId(agentId)).thenReturn(List.of());
        when(agentDao.updateSnapshotFields(any())).thenReturn(0);
        when(snapshotDao.insertWithNextVersion(any())).thenReturn(1);

        service.restoreSnapshot(agentId, targetId, currentStateToken(service, currentData));

        verify(pluginMappingService).deleteByAgentId(agentId);
        verify(pluginMappingService).saveBatch(argThat(mappings -> {
            AgentPluginMapping mapping = mappings.size() == 1 ? mappings.iterator().next() : null;
            return mapping != null
                    && "plugin".equals(mapping.getPluginId())
                    && mapping.getParamInfo().contains("target");
        }), eq(IRepository.DEFAULT_BATCH_SIZE));
        verify(snapshotDao).insertWithNextVersion(argThat(snapshot -> "restore".equals(snapshot.getSource())));
    }

    @Test
    void restoreSnapshotExplicitlyPersistsNullableFieldsAsNull() {
        AgentSnapshotDao snapshotDao = mock(AgentSnapshotDao.class);
        AgentDao agentDao = mock(AgentDao.class);
        AgentTagDao tagDao = mock(AgentTagDao.class);
        AgentPluginMappingService pluginMappingService = mock(AgentPluginMappingService.class);
        AgentContextProviderService contextProviderService = mock(AgentContextProviderService.class);
        AgentTagService tagService = mock(AgentTagService.class);
        CorrectWordFileService correctWordFileService = mock(CorrectWordFileService.class);
        AgentSnapshotServiceImpl service = new AgentSnapshotServiceImpl(snapshotDao, agentDao, tagDao, null,
                pluginMappingService, contextProviderService, tagService, null, null, correctWordFileService);
        ReflectionTestUtils.setField(service, "baseDao", snapshotDao);

        String agentId = "agent-id";
        String targetId = "target-id";
        AgentEntity lockedAgent = new AgentEntity();
        lockedAgent.setId(agentId);
        lockedAgent.setUserId(7L);
        lockedAgent.setTtsLanguage("普通话");
        lockedAgent.setTtsVolume(0);
        lockedAgent.setTtsRate(0);
        lockedAgent.setTtsPitch(0);
        lockedAgent.setSlmModelId("slm-id");
        lockedAgent.setVllmModelId("vllm-id");
        lockedAgent.setIntentModelId("intent-id");
        lockedAgent.setSystemPrompt("old prompt");

        AgentInfoVO currentInfo = snapshotAgentInfo(agentId, 7L, "same-name", "same-summary");
        currentInfo.setTtsLanguage("普通话");
        currentInfo.setTtsVolume(0);
        currentInfo.setTtsRate(0);
        currentInfo.setTtsPitch(0);
        currentInfo.setSlmModelId("slm-id");
        currentInfo.setVllmModelId("vllm-id");
        currentInfo.setIntentModelId("intent-id");
        currentInfo.setSystemPrompt("old prompt");
        AgentInfoVO restoredInfo = snapshotAgentInfo(agentId, 7L, "same-name", "same-summary");

        AgentSnapshotDataDTO currentData = snapshotData("same-name", "same-summary");
        currentData.setTtsLanguage("普通话");
        currentData.setTtsVolume(0);
        currentData.setTtsRate(0);
        currentData.setTtsPitch(0);
        currentData.setSlmModelId("slm-id");
        currentData.setVllmModelId("vllm-id");
        currentData.setIntentModelId("intent-id");
        currentData.setSystemPrompt("old prompt");
        AgentSnapshotDataDTO targetData = snapshotData("same-name", "same-summary");

        when(agentDao.selectByIdForUpdate(agentId)).thenReturn(lockedAgent);
        when(snapshotDao.selectById(targetId)).thenReturn(snapshotEntity(targetId, agentId, 2, targetData));
        when(agentDao.selectAgentInfoById(agentId)).thenReturn(currentInfo, restoredInfo);
        when(snapshotDao.selectLatestSnapshot(agentId))
                .thenReturn(snapshotEntity("latest-id", agentId, 5, currentData));
        when(contextProviderService.getByAgentId(agentId)).thenReturn(null);
        when(correctWordFileService.getAgentCorrectWordFileIds(agentId)).thenReturn(List.of());
        when(tagDao.selectByAgentId(agentId)).thenReturn(List.of());
        when(agentDao.updateSnapshotFields(any())).thenReturn(1);
        when(snapshotDao.insertWithNextVersion(any())).thenReturn(1);

        service.restoreSnapshot(agentId, targetId, currentStateToken(service, currentData));

        verify(agentDao).updateSnapshotFields(argThat(agent -> agent.getTtsLanguage() == null
                && agent.getTtsVolume() == null
                && agent.getTtsRate() == null
                && agent.getTtsPitch() == null
                && agent.getSlmModelId() == null
                && agent.getVllmModelId() == null
                && agent.getIntentModelId() == null
                && agent.getSystemPrompt() == null
                && Long.valueOf(7L).equals(agent.getUserId())));
        ArgumentCaptor<AgentSnapshotEntity> snapshotCaptor = ArgumentCaptor.forClass(AgentSnapshotEntity.class);
        verify(snapshotDao).insertWithNextVersion(snapshotCaptor.capture());
        AgentSnapshotDataDTO latestData = JsonUtils.parseObject(snapshotCaptor.getValue().getSnapshotData(),
                AgentSnapshotDataDTO.class);
        assertEquals("restore", snapshotCaptor.getValue().getSource());
        assertNull(latestData.getTtsLanguage());
        assertNull(latestData.getTtsVolume());
        assertNull(latestData.getTtsRate());
        assertNull(latestData.getTtsPitch());
        assertNull(latestData.getSlmModelId());
        assertNull(latestData.getVllmModelId());
        assertNull(latestData.getIntentModelId());
        assertNull(latestData.getSystemPrompt());
        verify(agentDao, org.mockito.Mockito.times(2)).selectAgentInfoById(agentId);
    }

    @Test
    void restoreSnapshotDoesNotMutateOrWriteHistoryWhenTargetMatchesCurrentState() {
        AgentSnapshotDao snapshotDao = mock(AgentSnapshotDao.class);
        AgentDao agentDao = mock(AgentDao.class);
        AgentTagDao tagDao = mock(AgentTagDao.class);
        AgentPluginMappingService pluginMappingService = mock(AgentPluginMappingService.class);
        AgentContextProviderService contextProviderService = mock(AgentContextProviderService.class);
        AgentTagService tagService = mock(AgentTagService.class);
        CorrectWordFileService correctWordFileService = mock(CorrectWordFileService.class);
        AgentSnapshotServiceImpl service = new AgentSnapshotServiceImpl(snapshotDao, agentDao, tagDao, null,
                pluginMappingService, contextProviderService, tagService, null, null, correctWordFileService);
        ReflectionTestUtils.setField(service, "baseDao", snapshotDao);

        String agentId = "agent-id";
        String targetId = "target-id";
        AgentEntity lockedAgent = new AgentEntity();
        lockedAgent.setId(agentId);
        AgentInfoVO currentInfo = snapshotAgentInfo(agentId, 7L, "same-name", "same-summary");
        AgentSnapshotDataDTO currentData = snapshotData("same-name", "same-summary");
        AgentSnapshotEntity target = snapshotEntity(targetId, agentId, 3, currentData);

        when(agentDao.selectByIdForUpdate(agentId)).thenReturn(lockedAgent);
        when(snapshotDao.selectById(targetId)).thenReturn(target);
        when(agentDao.selectAgentInfoById(agentId)).thenReturn(currentInfo);
        when(contextProviderService.getByAgentId(agentId)).thenReturn(null);
        when(correctWordFileService.getAgentCorrectWordFileIds(agentId)).thenReturn(List.of());
        when(tagDao.selectByAgentId(agentId)).thenReturn(List.of());

        service.restoreSnapshot(agentId, targetId, currentStateToken(service, currentData));

        verify(snapshotDao, never()).selectLatestSnapshot(agentId);
        verify(snapshotDao, never()).insertWithNextVersion(any());
        verify(snapshotDao, never()).deleteOlderThanKeepLimit(any(), anyInt());
        verify(agentDao, never()).updateSnapshotFields(any());
        verify(pluginMappingService, never()).deleteByAgentId(any());
        verify(contextProviderService, never()).saveOrUpdateByAgentId(any());
        verify(correctWordFileService, never()).saveAgentCorrectWords(any(), any());
        verify(tagService, never()).saveAgentTags(any(), any(), any());
    }

    @Test
    void deleteSnapshotRollsBackForAnyException() throws Exception {
        Method method = AgentSnapshotServiceImpl.class.getMethod("deleteSnapshot", String.class, String.class);

        Transactional transactional = method.getAnnotation(Transactional.class);

        assertNotNull(transactional);
        assertTrue(List.of(transactional.rollbackFor()).contains(Exception.class));
    }

    @Test
    void deleteSnapshotLocksAgentBeforeReadingAndDeletingSnapshot() {
        AgentSnapshotDao snapshotDao = mock(AgentSnapshotDao.class);
        AgentDao agentDao = mock(AgentDao.class);
        AgentSnapshotServiceImpl service = new AgentSnapshotServiceImpl(snapshotDao, agentDao, null, null, null, null,
                null, null, null, null);
        ReflectionTestUtils.setField(service, "baseDao", snapshotDao);

        String agentId = "agent-id";
        String snapshotId = "snapshot-id";
        AgentEntity agent = new AgentEntity();
        agent.setId(agentId);
        AgentSnapshotEntity snapshot = new AgentSnapshotEntity();
        snapshot.setId(snapshotId);
        snapshot.setAgentId(agentId);
        snapshot.setVersionNo(2);

        when(agentDao.selectByIdForUpdate(agentId)).thenReturn(agent);
        when(snapshotDao.selectById(snapshotId)).thenReturn(snapshot);
        when(snapshotDao.selectMaxVersionNo(agentId)).thenReturn(3);
        when(snapshotDao.deleteById(snapshotId)).thenReturn(1);

        service.deleteSnapshot(agentId, snapshotId);

        InOrder order = inOrder(agentDao, snapshotDao);
        order.verify(agentDao).selectByIdForUpdate(agentId);
        order.verify(snapshotDao).selectById(snapshotId);
        order.verify(snapshotDao).selectMaxVersionNo(agentId);
        order.verify(snapshotDao).deleteById(snapshotId);
    }

    @Test
    void snapshotInsertAllocatesVersionInSingleSqlStatement() throws Exception {
        String xml = normalizeWhitespace(Files.readString(Path.of("src/main/resources/mapper/agent/AgentSnapshotDao.xml")));
        String dao = Files.readString(Path.of("src/main/java/xiaozhi/modules/agent/dao/AgentSnapshotDao.java"));

        assertTrue(dao.contains("insertWithNextVersion"));
        assertTrue(xml.contains("<insert id=\"insertWithNextVersion\">"));
        assertTrue(xml.contains("INSERT INTO ai_agent_snapshot"));
        assertTrue(xml.contains("COALESCE(MAX(version_no), 0) + 1"));
        assertFalse(xml.contains("LAST_INSERT_ID"));
        assertFalse(xml.contains("ai_agent_snapshot_sequence"));
    }

    @Test
    void restoreUpdateSqlWritesNullableSnapshotFieldsWithoutOwnershipColumns() throws Exception {
        String xml = Files.readString(Path.of("src/main/resources/mapper/agent/AgentDao.xml"));
        int updateStart = xml.indexOf("<update id=\"updateSnapshotFields\">");
        int updateEnd = xml.indexOf("</update>", updateStart);
        assertTrue(updateStart >= 0);
        assertTrue(updateEnd > updateStart);
        String updateSql = normalizeWhitespace(xml.substring(updateStart, updateEnd));

        for (AgentSnapshotField field : AgentSnapshotField.values()) {
            if (!field.isRestorableAgentField()) {
                continue;
            }
            String column = field.getFieldName().replaceAll("([a-z0-9])([A-Z])", "$1_$2")
                    .toLowerCase(Locale.ROOT);
            assertTrue(updateSql.contains(column + " = #{agent." + field.getFieldName() + ","),
                    () -> "Missing explicit restore assignment for " + field.getFieldName());
        }
        assertTrue(updateSql.contains("tts_language = #{agent.ttsLanguage,jdbcType=VARCHAR}"));
        assertTrue(updateSql.contains("tts_volume = #{agent.ttsVolume,jdbcType=INTEGER}"));
        assertTrue(updateSql.contains("slm_model_id = #{agent.slmModelId,jdbcType=VARCHAR}"));
        assertTrue(updateSql.contains("vllm_model_id = #{agent.vllmModelId,jdbcType=VARCHAR}"));
        assertTrue(updateSql.contains("intent_model_id = #{agent.intentModelId,jdbcType=VARCHAR}"));
        assertTrue(updateSql.contains("system_prompt = #{agent.systemPrompt,jdbcType=LONGVARCHAR}"));
        assertTrue(updateSql.contains("summary_memory = #{agent.summaryMemory,jdbcType=LONGVARCHAR}"));
        assertFalse(updateSql.contains("user_id ="));
        assertFalse(updateSql.contains("creator ="));
        assertFalse(updateSql.contains("created_at ="));
    }

    @Test
    void snapshotMigrationIsMergedIntoSingleChangeLog() throws Exception {
        String sql = Files.readString(Path.of("src/main/resources/db/changelog/202607071530.sql"));
        String master = Files.readString(Path.of("src/main/resources/db/changelog/db.changelog-master.yaml"));

        assertTrue(sql.contains("restore_from_snapshot_id"));
        assertTrue(sql.contains("restore_from_version_no"));
        assertTrue(sql.contains("idx_snapshot_user_created_at"));
        assertTrue(sql.contains("DEFAULT (JSON_OBJECT())"));
        assertTrue(master.contains("202607071530.sql"));
        assertFalse(master.contains("202607081150.sql"));
        assertFalse(master.contains("202607081230.sql"));
    }

    @Test
    void legacySnapshotRedactionHasItsOwnResumableSchemaVersionChangeLog() throws Exception {
        String sql = Files.readString(Path.of("src/main/resources/db/changelog/202607101200.sql"));
        String master = Files.readString(Path.of("src/main/resources/db/changelog/db.changelog-master.yaml"));
        String mapper = Files.readString(Path.of("src/main/resources/mapper/agent/AgentSnapshotDao.xml"));

        assertTrue(sql.contains("redaction_version"));
        assertTrue(sql.contains("idx_snapshot_redaction_version_id"));
        assertTrue(sql.contains("-- rollback"));
        assertTrue(master.contains("202607101200.sql"));
        assertTrue(mapper.contains("selectLegacyRedactionBatch"));
        assertTrue(mapper.contains("redaction_version &lt; #{targetRedactionVersion}"));
        assertTrue(mapper.contains("<update id=\"updateRedactedSnapshots\">"));
    }

    @Test
    void selectNextSnapshotLoadsRestoreTraceColumnsWithoutPreviousVersionQuery() throws Exception {
        String xml = normalizeWhitespace(Files.readString(Path.of("src/main/resources/mapper/agent/AgentSnapshotDao.xml")));
        String dao = Files.readString(Path.of("src/main/java/xiaozhi/modules/agent/dao/AgentSnapshotDao.java"));

        assertTrue(xml.contains("restore_from_snapshot_id AS restoreFromSnapshotId"));
        assertTrue(xml.contains("restore_from_version_no AS restoreFromVersionNo"));
        assertTrue(xml.contains("version_no &gt; #{versionNo}"));
        assertFalse(xml.contains("selectPreviousSnapshot"));
        assertFalse(dao.contains("selectPreviousSnapshot"));
    }

    @Test
    void retentionPruneSqlKeepsLatestVersions() throws Exception {
        String xml = Files.readString(Path.of("src/main/resources/mapper/agent/AgentSnapshotDao.xml"));

        assertTrue(xml.contains("deleteOlderThanKeepLimit"));
        assertTrue(xml.contains("ORDER BY version_no DESC"));
        assertTrue(xml.contains("LIMIT #{keepLimit}"));
    }

    @Test
    void agentInfoMapperLoadsFunctionsWithJoinInsteadOfNestedSelect() throws Exception {
        String xml = Files.readString(Path.of("src/main/resources/mapper/agent/AgentDao.xml"));

        assertTrue(xml.contains("LEFT JOIN ai_agent_plugin_mapping f ON f.agent_id = a.id"));
        assertFalse(xml.contains("selectAgentFunctionsByAgentId"));
        assertFalse(xml.contains("select=\"selectAgentFunctions"));
    }

    @Test
    void toVOIncludesRestoreTraceFields() throws Exception {
        AgentSnapshotServiceImpl service = new AgentSnapshotServiceImpl(null, null, null, null, null, null, null, null,
                null, null);
        Method method = AgentSnapshotServiceImpl.class.getDeclaredMethod("toVO",
                AgentSnapshotEntity.class, boolean.class);
        method.setAccessible(true);

        AgentSnapshotEntity entity = new AgentSnapshotEntity();
        entity.setId("snapshot-id");
        entity.setAgentId("agent-id");
        entity.setVersionNo(3);
        entity.setChangedFields("[]");
        entity.setSource("restore");
        entity.setRestoreFromSnapshotId("target-id");
        entity.setRestoreFromVersionNo(1);

        AgentSnapshotVO vo = (AgentSnapshotVO) method.invoke(service, entity, false);

        assertEquals("target-id", vo.getRestoreFromSnapshotId());
        assertEquals(1, vo.getRestoreFromVersionNo());
    }

    @Test
    void toVOKeepsStoredEventFieldsStableAcrossDeletedVersionGapAndMetadataChanges() throws Exception {
        AgentSnapshotDao snapshotDao = mock(AgentSnapshotDao.class);
        AgentSnapshotServiceImpl service = new AgentSnapshotServiceImpl(snapshotDao, null, null, null, null, null, null,
                null, null, null);
        Method method = AgentSnapshotServiceImpl.class.getDeclaredMethod("toVO",
                AgentSnapshotEntity.class, boolean.class);
        method.setAccessible(true);

        AgentSnapshotEntity current = new AgentSnapshotEntity();
        current.setId("snapshot-id");
        current.setAgentId("agent-id");
        current.setVersionNo(3);
        current.setChangedFields(JsonUtils.toJsonString(List.of("ttsLanguage", "ttsVolume")));

        AgentSnapshotVO vo = (AgentSnapshotVO) method.invoke(service, current, false);

        assertEquals(List.of("ttsLanguage", "ttsVolume"), vo.getChangedFields());
        verifyNoInteractions(snapshotDao);
    }

    @Test
    void pageUsesPersistedChangedFieldsWithoutPerRecordQueries() {
        AgentSnapshotDao snapshotDao = mock(AgentSnapshotDao.class);
        AgentSnapshotServiceImpl service = new AgentSnapshotServiceImpl(snapshotDao, null, null, null, null, null, null,
                null, null, null);

        AgentSnapshotEntity versionFive = new AgentSnapshotEntity();
        versionFive.setVersionNo(5);
        versionFive.setChangedFields(JsonUtils.toJsonString(List.of("agentName")));
        AgentSnapshotEntity versionThree = new AgentSnapshotEntity();
        versionThree.setVersionNo(3);
        versionThree.setChangedFields(JsonUtils.toJsonString(List.of("ttsLanguage")));
        Page<AgentSnapshotEntity> result = new Page<>(1, 10);
        result.setRecords(List.of(versionFive, versionThree));
        result.setTotal(2);
        when(snapshotDao.selectPage(any(), any())).thenReturn(result);

        List<AgentSnapshotVO> records = service.page("agent-id", new AgentSnapshotPageDTO()).getList();

        assertEquals(List.of("agentName"), records.get(0).getChangedFields());
        assertEquals(List.of("ttsLanguage"), records.get(1).getChangedFields());
        verify(snapshotDao).selectPage(any(), any());
        verifyNoMoreInteractions(snapshotDao);
    }

    @Test
    void pageDoesNotCreateInitialSnapshotWhenAgentHasNoHistory() {
        AgentSnapshotDao snapshotDao = mock(AgentSnapshotDao.class);
        AgentDao agentDao = mock(AgentDao.class);
        AgentSnapshotServiceImpl service = new AgentSnapshotServiceImpl(snapshotDao, agentDao, null, null, null,
                null, null, null, null, null);

        when(snapshotDao.selectPage(any(), any())).thenReturn(new Page<AgentSnapshotEntity>(1, 10));

        service.page("agent-id", new AgentSnapshotPageDTO());

        verify(agentDao, never()).selectByIdForUpdate(any());
        verify(snapshotDao, never()).selectMaxVersionNo(any());
        verify(snapshotDao, never()).insertWithNextVersion(any());
        verify(snapshotDao, never()).deleteOlderThanKeepLimit(any(), anyInt());
    }

    @Test
    void getCurrentVersionNoReturnsPersistedMaxVersion() {
        AgentSnapshotDao snapshotDao = mock(AgentSnapshotDao.class);
        AgentSnapshotServiceImpl service = new AgentSnapshotServiceImpl(snapshotDao, null, null, null, null,
                null, null, null, null, null);

        when(snapshotDao.selectMaxVersionNo("agent-id")).thenReturn(7);

        assertEquals(7, service.getCurrentVersionNo("agent-id"));
    }

    @Test
    void createSnapshotStoresCurrentStateAsInitialVersionWhenHistoryIsEmpty() {
        AgentSnapshotDao snapshotDao = mock(AgentSnapshotDao.class);
        AgentDao agentDao = mock(AgentDao.class);
        AgentTagDao tagDao = mock(AgentTagDao.class);
        AgentContextProviderService contextProviderService = mock(AgentContextProviderService.class);
        CorrectWordFileService correctWordFileService = mock(CorrectWordFileService.class);
        AgentSnapshotServiceImpl service = new AgentSnapshotServiceImpl(snapshotDao, agentDao, tagDao, null, null,
                contextProviderService, null, null, null, correctWordFileService);

        AgentEntity lockedAgent = new AgentEntity();
        lockedAgent.setId("agent-id");
        AgentInfoVO agentInfo = new AgentInfoVO();
        agentInfo.setId("agent-id");
        agentInfo.setUserId(7L);
        agentInfo.setAgentName("agent");
        when(agentDao.selectByIdForUpdate("agent-id")).thenReturn(lockedAgent);
        when(agentDao.selectAgentInfoById("agent-id")).thenReturn(agentInfo);
        when(snapshotDao.selectLatestSnapshot("agent-id")).thenReturn(null);
        when(snapshotDao.insertWithNextVersion(any())).thenReturn(1);
        when(correctWordFileService.getAgentCorrectWordFileIds("agent-id")).thenReturn(List.of());
        when(contextProviderService.getByAgentId("agent-id")).thenReturn(null);
        when(tagDao.selectByAgentId("agent-id")).thenReturn(List.of());

        service.createSnapshot("agent-id", "config");

        verify(snapshotDao).insertWithNextVersion(argThat(snapshot -> "config".equals(snapshot.getSource())
                && snapshot.getVersionNo() == null
                && snapshot.getChangedFields().contains("initial")));
        verify(snapshotDao).deleteOlderThanKeepLimit("agent-id", 100);
    }

    @Test
    void restoreTagRejectsSoftDeletedSnapshotTagWithoutMutatingGlobalTag() throws Exception {
        AgentTagDao tagDao = mock(AgentTagDao.class);
        AgentSnapshotServiceImpl service = new AgentSnapshotServiceImpl(null, null, tagDao, null, null, null, null, null,
                null, null);
        Method method = AgentSnapshotServiceImpl.class.getDeclaredMethod("restoreTag",
                AgentSnapshotTagDTO.class, Date.class);
        method.setAccessible(true);

        AgentTagEntity deletedTag = new AgentTagEntity();
        deletedTag.setId("deleted-tag-id");
        deletedTag.setTagName("archived");
        deletedTag.setDeleted(1);
        when(tagDao.selectById("deleted-tag-id")).thenReturn(deletedTag);

        AgentSnapshotTagDTO snapshotTag = new AgentSnapshotTagDTO();
        snapshotTag.setId("deleted-tag-id");
        snapshotTag.setTagName("archived");

        InvocationTargetException error = assertThrows(InvocationTargetException.class,
                () -> method.invoke(service, snapshotTag, new Date()));

        assertTrue(error.getCause() instanceof RenException);
        assertEquals("快照引用的标签已被删除，无法恢复，请先重新创建或选择标签", error.getCause().getMessage());
        verify(tagDao, never()).updateById(any(AgentTagEntity.class));
        verify(tagDao, never()).insert(any(AgentTagEntity.class));
    }

    private AgentInfoVO snapshotAgentInfo(String agentId, Long userId, String agentName, String summaryMemory) {
        AgentInfoVO info = new AgentInfoVO();
        info.setId(agentId);
        info.setUserId(userId);
        info.setAgentName(agentName);
        info.setSummaryMemory(summaryMemory);
        info.setChatHistoryConf(0);
        return info;
    }

    private AgentSnapshotDataDTO snapshotData(String agentName, String summaryMemory) {
        AgentSnapshotDataDTO data = new AgentSnapshotDataDTO();
        data.setAgentName(agentName);
        data.setSummaryMemory(summaryMemory);
        data.setChatHistoryConf(0);
        return data;
    }

    private AgentSnapshotDataDTO buildExtendedSensitiveSnapshot() {
        AgentSnapshotDataDTO data = new AgentSnapshotDataDTO();
        AgentUpdateDTO.FunctionInfo function = new AgentUpdateDTO.FunctionInfo();
        function.setPluginId("rag");
        Map<String, Object> params = new LinkedHashMap<>();
        params.put("api_key", "secret-api-key");
        params.put("Cookie", "secret-cookie");
        params.put("Set-Cookie", "secret-set-cookie");
        params.put("Proxy-Authorization", "secret-proxy-authorization");
        params.put("X-Session-ID", "secret-session-id");
        params.put("X-Auth", "secret-auth-header");
        params.put("slackWebhookUrl",
                "https://hooks.slack.com/services/T111/B222/secret-slack-path");
        params.put("max_tokens", 32);
        function.setParamInfo(params);

        ContextProviderDTO provider = new ContextProviderDTO();
        provider.setUrl("https://discord.com/api/webhooks/123456/secret-discord-path");
        Map<String, Object> headers = new LinkedHashMap<>();
        headers.put("Authorization", "secret-authorization");
        headers.put("Cookie", "secret-context-cookie");
        headers.put("PHPSESSID", "secret-php-session");
        headers.put("X-Session", "secret-x-session");
        headers.put("Accept", "application/json");
        provider.setHeaders(headers);

        data.setFunctions(List.of(function));
        data.setContextProviders(List.of(provider));
        return data;
    }

    private AgentUpdateDTO.FunctionInfo functionInfo(String pluginId, Map<String, Object> params) {
        AgentUpdateDTO.FunctionInfo function = new AgentUpdateDTO.FunctionInfo();
        function.setPluginId(pluginId);
        function.setParamInfo(params);
        return function;
    }

    private void assertExtendedSecretsAbsent(String json) {
        for (String secret : List.of(
                "secret-api-key",
                "secret-cookie",
                "secret-set-cookie",
                "secret-proxy-authorization",
                "secret-session-id",
                "secret-auth-header",
                "secret-slack-path",
                "secret-discord-path",
                "secret-authorization",
                "secret-context-cookie",
                "secret-php-session",
                "secret-x-session")) {
            assertFalse(json.contains(secret), () -> "Sensitive value leaked: " + secret);
        }
    }

    private AgentSnapshotEntity snapshotEntity(String snapshotId, String agentId, Integer versionNo,
            AgentSnapshotDataDTO data) {
        AgentSnapshotEntity entity = new AgentSnapshotEntity();
        entity.setId(snapshotId);
        entity.setAgentId(agentId);
        entity.setUserId(7L);
        entity.setVersionNo(versionNo);
        entity.setSnapshotData(JsonUtils.toJsonString(data));
        entity.setChangedFields("[]");
        return entity;
    }

    private AgentSnapshotDataDTO buildSnapshot(String apiKey, String authToken, String description) {
        AgentSnapshotDataDTO data = new AgentSnapshotDataDTO();

        AgentUpdateDTO.FunctionInfo function = new AgentUpdateDTO.FunctionInfo();
        function.setPluginId("rag");
        HashMap<String, Object> params = new HashMap<>();
        params.put("api_key", apiKey);
        params.put("description", description);
        function.setParamInfo(params);

        ContextProviderDTO provider = new ContextProviderDTO();
        provider.setUrl("https://example.com/context");
        provider.setHeaders(Map.of("Authorization", authToken));

        data.setFunctions(List.of(function));
        data.setContextProviders(List.of(provider));
        return data;
    }

    private AgentSnapshotDataDTO nestedWebhookSnapshot(String secret) {
        AgentSnapshotDataDTO data = new AgentSnapshotDataDTO();
        data.setFunctions(List.of(functionInfo("plugin", Map.of(
                "webhookConfig", Map.of(
                        "value", "https://capability.example.com/public/" + secret)))));
        return data;
    }

    private String currentStateToken(AgentSnapshotServiceImpl service, AgentSnapshotDataDTO data) {
        return ReflectionTestUtils.invokeMethod(service, "buildCurrentStateToken", data);
    }

    private String normalizeWhitespace(String value) {
        return value.replaceAll("\\s+", " ").trim();
    }
}
