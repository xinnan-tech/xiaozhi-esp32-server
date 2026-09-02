package xiaozhi.modules.device.service.impl;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.stream.Stream;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;
import org.junit.jupiter.params.provider.NullAndEmptySource;
import org.junit.jupiter.params.provider.ValueSource;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpServer;

import cn.hutool.crypto.digest.DigestUtil;

@DisplayName("MQTT Gateway 日期鉴权回归测试")
class MqttGatewayAuthorizationTest {

    private static final String SIGNATURE_KEY = "test-signature-key";
    private static final Instant FIXED_INSTANT = Instant.parse("2026-07-14T00:30:00Z");

    private HttpServer server;

    @AfterEach
    void stopServer() {
        if (server != null) {
            server.stop(0);
        }
    }

    @Test
    @DisplayName("以 UTC 日期生成当天、前一天和后一天三个候选 token")
    void generatesUtcDateCandidates() {
        List<String> tokens = MqttGatewayAuthorization.generateDailyTokens(SIGNATURE_KEY, FIXED_INSTANT);

        assertEquals(List.of(
                tokenFor("2026-07-14"),
                tokenFor("2026-07-13"),
                tokenFor("2026-07-15")), tokens);
    }

    @ParameterizedTest(name = "Gateway 时区 {0}")
    @MethodSource("gatewayTimeZones")
    @DisplayName("候选 token 覆盖上海和圣保罗 Gateway 的本地日期")
    void coversGatewayLocalDate(String gatewayTimeZone, Instant now, int expectedTokenIndex) {
        String gatewayDate = now.atZone(ZoneId.of(gatewayTimeZone)).toLocalDate().toString();
        List<String> tokens = MqttGatewayAuthorization.generateDailyTokens(SIGNATURE_KEY, now);

        assertEquals(tokenFor(gatewayDate), tokens.get(expectedTokenIndex));
    }

    @Test
    @DisplayName("仅在 401 时按日期候选重试并保留请求体")
    void retriesOnlyAuthenticationFailures() throws IOException {
        AtomicInteger requestCount = new AtomicInteger();
        List<String> authorizationHeaders = new ArrayList<>();
        List<String> requestBodies = new ArrayList<>();
        List<String> expectedTokens = MqttGatewayAuthorization.generateDailyTokens(SIGNATURE_KEY, FIXED_INSTANT);
        startServer(exchange -> {
            int attempt = requestCount.getAndIncrement();
            authorizationHeaders.add(exchange.getRequestHeaders().getFirst("Authorization"));
            requestBodies.add(new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8));
            if (attempt == 0) {
                respond(exchange, 401, "{\"error\":\"unauthorized\"}");
            } else if (attempt == 1) {
                respond(exchange, 401, "{\"error\":\"unauthorized\"}");
            } else {
                respond(exchange, 200, "{\"online\":true}");
            }
        });

        String requestBody = "{\"clientIds\":[\"device-id\"]}";
        String response = MqttGatewayAuthorization.postJson(
                serverUrl(), requestBody, SIGNATURE_KEY, FIXED_INSTANT);

        assertEquals("{\"online\":true}", response);
        assertEquals(3, requestCount.get());
        assertEquals(expectedTokens.stream().map(token -> "Bearer " + token).toList(), authorizationHeaders);
        assertEquals(List.of(requestBody, requestBody, requestBody), requestBodies);
    }

    @ParameterizedTest(name = "HTTP {0}")
    @ValueSource(ints = { 403, 500 })
    @DisplayName("非 401 错误不重试且向上抛出")
    void doesNotRetryNonAuthenticationFailure(int statusCode) throws IOException {
        AtomicInteger requestCount = new AtomicInteger();
        startServer(exchange -> {
            requestCount.incrementAndGet();
            exchange.getRequestBody().readAllBytes();
            respond(exchange, statusCode, "{\"error\":\"request rejected\"}");
        });

        MqttGatewayAuthorization.GatewayRequestException exception = assertThrows(
                MqttGatewayAuthorization.GatewayRequestException.class,
                () -> MqttGatewayAuthorization.postJson(
                        serverUrl(), "{}", SIGNATURE_KEY, FIXED_INSTANT));

        assertEquals(statusCode, exception.statusCode());
        assertEquals(1, requestCount.get());
    }

    @Test
    @DisplayName("所有日期候选被拒绝时不把错误响应当作设备离线数据")
    void propagatesAuthenticationFailureAfterAllCandidatesAreRejected() throws IOException {
        AtomicInteger requestCount = new AtomicInteger();
        startServer(exchange -> {
            requestCount.incrementAndGet();
            exchange.getRequestBody().readAllBytes();
            respond(exchange, 401, "{\"error\":\"unauthorized\"}");
        });

        MqttGatewayAuthorization.GatewayRequestException exception = assertThrows(
                MqttGatewayAuthorization.GatewayRequestException.class,
                () -> MqttGatewayAuthorization.postJson(
                        serverUrl(), "{}", SIGNATURE_KEY, FIXED_INSTANT));

        assertEquals(401, exception.statusCode());
        assertEquals(3, requestCount.get());
    }

    @ParameterizedTest(name = "密钥值 [{0}]")
    @NullAndEmptySource
    @ValueSource(strings = { " ", "null", " NULL " })
    @DisplayName("缺少或占位签名密钥时在发起 HTTP 请求前失败")
    void rejectsMissingSignatureKeyBeforeSendingRequest(String signatureKey) {
        MqttGatewayAuthorization.GatewayRequestException exception = assertThrows(
                MqttGatewayAuthorization.GatewayRequestException.class,
                () -> MqttGatewayAuthorization.postJson(
                        "http://127.0.0.1:1", "{}", signatureKey, FIXED_INSTANT));

        assertNull(exception.statusCode());
    }

    private static Stream<Arguments> gatewayTimeZones() {
        return Stream.of(
                Arguments.of("Asia/Shanghai", Instant.parse("2026-07-13T17:30:00Z"), 2),
                Arguments.of("America/Sao_Paulo", Instant.parse("2026-07-14T00:30:00Z"), 1));
    }

    private void startServer(HttpHandler handler) throws IOException {
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/mqtt", handler);
        server.start();
    }

    private String serverUrl() {
        assertTrue(server != null, "test server must be started");
        return "http://127.0.0.1:" + server.getAddress().getPort() + "/mqtt";
    }

    private static void respond(HttpExchange exchange, int statusCode, String body) throws IOException {
        byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
        exchange.getResponseHeaders().set("Content-Type", "application/json");
        exchange.sendResponseHeaders(statusCode, bytes.length);
        try (var output = exchange.getResponseBody()) {
            output.write(bytes);
        }
    }

    private static String tokenFor(String date) {
        return DigestUtil.sha256Hex(date + SIGNATURE_KEY);
    }
}
