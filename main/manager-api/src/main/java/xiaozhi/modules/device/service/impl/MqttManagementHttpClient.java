package xiaozhi.modules.device.service.impl;

import java.time.Instant;

import cn.hutool.json.JSONUtil;

class MqttManagementHttpClient {

    private final int timeoutMillis;

    MqttManagementHttpClient() {
        this(5000);
    }

    MqttManagementHttpClient(int timeoutMillis) {
        this.timeoutMillis = timeoutMillis;
    }

    Response post(
            MqttManagementEndpointResolver.Endpoint endpoint,
            String path,
            Object requestBody) {
        String url = appendPath(endpoint.baseUrl(), path);
        MqttGatewayAuthorization.GatewayResponse response =
                MqttGatewayAuthorization.postJsonResponse(
                        url,
                        JSONUtil.toJsonStr(requestBody),
                        endpoint.signatureKey(),
                        Instant.now(),
                        timeoutMillis);
        return new Response(
                endpoint.backend(),
                response.statusCode(),
                response.body());
    }

    static String appendPath(String baseUrl, String path) {
        String normalizedBase = baseUrl.endsWith("/")
                ? baseUrl.substring(0, baseUrl.length() - 1)
                : baseUrl;
        String normalizedPath = path.startsWith("/")
                ? path
                : "/" + path;
        return normalizedBase + normalizedPath;
    }

    record Response(
            MqttManagementEndpointResolver.Backend backend,
            int statusCode,
            String body) {

        boolean isSuccessfulHttp() {
            return statusCode >= 200 && statusCode < 300;
        }
    }
}
