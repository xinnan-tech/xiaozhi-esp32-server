package xiaozhi.modules.device.service.impl;

import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.List;
import java.util.function.Function;

import org.apache.commons.lang3.StringUtils;

import cn.hutool.crypto.digest.DigestUtil;
import cn.hutool.http.ContentType;
import cn.hutool.http.Header;
import cn.hutool.http.HttpRequest;
import cn.hutool.http.HttpResponse;

final class MqttGatewayAuthorization {

    private static final int HTTP_UNAUTHORIZED = 401;
    private static final int DEFAULT_TIMEOUT_MILLIS = 10000;

    private MqttGatewayAuthorization() {
    }

    static String postJson(String url, String jsonBody, String signatureKey, Instant now) {
        return postJson(url, jsonBody, signatureKey, now, DEFAULT_TIMEOUT_MILLIS);
    }

    static String postJson(String url, String jsonBody, String signatureKey, Instant now, int timeoutMillis) {
        GatewayResponse response = executeWithDateFallback(
                signatureKey,
                now,
                token -> executeRequest(url, jsonBody, token, timeoutMillis));

        if (response.statusCode() < 200 || response.statusCode() >= 300) {
            throw new GatewayRequestException(
                    "MQTT Gateway request failed with HTTP status " + response.statusCode(),
                    response.statusCode());
        }
        return response.body();
    }

    static List<String> generateDailyTokens(String signatureKey, Instant now) {
        if (isMissingSignatureKey(signatureKey)) {
            throw new GatewayRequestException("MQTT Gateway signature key is empty", null);
        }

        LocalDate utcDate = now.atZone(ZoneOffset.UTC).toLocalDate();
        return List.of(
                tokenFor(utcDate, signatureKey),
                tokenFor(utcDate.minusDays(1), signatureKey),
                tokenFor(utcDate.plusDays(1), signatureKey));
    }

    static GatewayResponse executeWithDateFallback(String signatureKey, Instant now,
            Function<String, GatewayResponse> requestExecutor) {
        GatewayResponse lastAuthenticationFailure = null;
        for (String token : generateDailyTokens(signatureKey, now)) {
            GatewayResponse response = requestExecutor.apply(token);
            if (!isAuthenticationFailure(response.statusCode())) {
                return response;
            }
            lastAuthenticationFailure = response;
        }

        Integer statusCode = lastAuthenticationFailure == null ? null : lastAuthenticationFailure.statusCode();
        throw new GatewayRequestException(
                "MQTT Gateway rejected all daily authorization tokens"
                        + (statusCode == null ? "" : " (HTTP " + statusCode + ")"),
                statusCode);
    }

    private static String tokenFor(LocalDate date, String signatureKey) {
        return DigestUtil.sha256Hex(date + signatureKey);
    }

    private static boolean isAuthenticationFailure(int statusCode) {
        return statusCode == HTTP_UNAUTHORIZED;
    }

    static boolean isMissingSignatureKey(String signatureKey) {
        return StringUtils.isBlank(signatureKey) || "null".equalsIgnoreCase(signatureKey.trim());
    }

    private static GatewayResponse executeRequest(String url, String jsonBody, String token, int timeoutMillis) {
        try (HttpResponse response = HttpRequest.post(url)
                .header(Header.CONTENT_TYPE, ContentType.JSON.getValue())
                .header(Header.AUTHORIZATION, "Bearer " + token)
                .body(jsonBody)
                .timeout(timeoutMillis)
                .execute()) {
            return new GatewayResponse(response.getStatus(), response.body());
        }
    }

    record GatewayResponse(int statusCode, String body) {
    }

    static final class GatewayRequestException extends RuntimeException {
        private final Integer statusCode;

        GatewayRequestException(String message, Integer statusCode) {
            super(message);
            this.statusCode = statusCode;
        }

        Integer statusCode() {
            return statusCode;
        }
    }
}
