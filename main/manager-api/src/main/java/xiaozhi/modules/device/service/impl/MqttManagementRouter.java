package xiaozhi.modules.device.service.impl;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

import cn.hutool.json.JSONObject;
import cn.hutool.json.JSONUtil;

final class MqttManagementRouter {

    private final MqttManagementEndpointResolver endpointResolver;
    private final MqttManagementHttpClient httpClient;

    MqttManagementRouter(
            MqttManagementEndpointResolver endpointResolver,
            MqttManagementHttpClient httpClient) {
        this.endpointResolver = endpointResolver;
        this.httpClient = httpClient;
    }

    String getMergedStatus(Set<String> clientIds) {
        List<MqttManagementEndpointResolver.Endpoint> endpoints =
                endpointResolver.resolve();
        if (endpoints.isEmpty()) {
            return "";
        }

        Map<String, MutableDeviceStatus> merged =
                initializeStatuses(clientIds);
        int successfulBackends = 0;
        RuntimeException lastFailure = null;
        for (MqttManagementEndpointResolver.Endpoint endpoint : endpoints) {
            try {
                MqttManagementHttpClient.Response response =
                        httpClient.post(
                                endpoint,
                                "/api/devices/status",
                                Map.of("clientIds", clientIds));
                if (!response.isSuccessfulHttp()) {
                    throw new IllegalStateException(
                            "MQTT管理状态查询失败: "
                                    + response.statusCode());
                }
                mergeStatusResponse(
                        merged, endpoint.backend(), response.body());
                successfulBackends++;
            } catch (RuntimeException e) {
                lastFailure = e;
            }
        }

        if (lastFailure != null
                || successfulBackends != endpoints.size()) {
            throw new ManagementUnavailableException(
                    "无法确认全部MQTT后端状态", lastFailure);
        }

        Map<String, Object> result = new LinkedHashMap<>();
        merged.forEach((clientId, status) ->
                result.put(clientId, status.toMap()));
        return JSONUtil.toJsonStr(result);
    }

    MqttManagementHttpClient.Response sendReadOnlyCommand(
            String clientId, Object requestBody) {
        return sendReadOnlyCommand(clientId, requestBody, null);
    }

    MqttManagementHttpClient.Response sendReadOnlyCommand(
            String clientId,
            Object requestBody,
            MqttManagementEndpointResolver.Backend preferredBackend) {
        List<MqttManagementEndpointResolver.Endpoint> endpoints =
                endpointResolver.resolve();
        if (endpoints.isEmpty()) {
            return null;
        }
        if (preferredBackend != null) {
            MqttManagementEndpointResolver.Endpoint endpoint =
                    endpoints.stream()
                            .filter(candidate ->
                                    candidate.backend()
                                            == preferredBackend)
                            .findFirst()
                            .orElseThrow(() ->
                                    new ManagementUnavailableException(
                                            "分页MQTT后端配置已变化",
                                            null));
            return sendCommand(endpoint, clientId, requestBody);
        }

        MqttManagementHttpClient.Response lastResponse = null;
        RuntimeException lastFailure = null;
        for (MqttManagementEndpointResolver.Endpoint endpoint : endpoints) {
            try {
                MqttManagementHttpClient.Response response =
                        sendCommand(endpoint, clientId, requestBody);
                lastResponse = response;
                if (isCommandSuccess(response)) {
                    return response;
                }
            } catch (RuntimeException e) {
                lastFailure = e;
            }
        }
        if (lastResponse != null) {
            return lastResponse;
        }
        throw new ManagementUnavailableException(
                "MQTT管理服务均不可用", lastFailure);
    }

    MqttManagementHttpClient.Response sendMutatingCommand(
            String clientId, Object requestBody) {
        List<MqttManagementEndpointResolver.Endpoint> endpoints =
                endpointResolver.resolve();
        if (endpoints.isEmpty()) {
            return null;
        }

        List<MqttManagementEndpointResolver.Endpoint> online =
                new ArrayList<>();
        int successfulStatusBackends = 0;
        RuntimeException lastStatusFailure = null;
        for (MqttManagementEndpointResolver.Endpoint endpoint : endpoints) {
            try {
                MqttManagementHttpClient.Response statusResponse =
                        httpClient.post(
                                endpoint,
                                "/api/devices/status",
                                Map.of("clientIds", Set.of(clientId)));
                if (!statusResponse.isSuccessfulHttp()) {
                    throw new IllegalStateException(
                            "MQTT管理状态查询失败: "
                                    + statusResponse.statusCode());
                }
                Map<String, BackendDeviceStatus> statuses =
                        parseStatusResponse(
                                statusResponse.body(),
                                Set.of(clientId));
                successfulStatusBackends++;
                if (statuses.get(clientId).exists()) {
                    online.add(endpoint);
                }
            } catch (RuntimeException e) {
                lastStatusFailure = e;
            }
        }

        if (lastStatusFailure != null
                || successfulStatusBackends != endpoints.size()) {
            throw new ManagementUnavailableException(
                    "无法确认设备所在的MQTT后端",
                    lastStatusFailure);
        }
        if (online.isEmpty()) {
            return offlineResponse(endpoints.get(0).backend());
        }
        if (online.size() > 1) {
            return commandErrorResponse(
                    endpoints.get(0).backend(),
                    409,
                    "设备同时存在于多个MQTT后端",
                    "DEVICE_BACKEND_AMBIGUOUS");
        }

        return sendCommand(online.get(0), clientId, requestBody);
    }

    MqttManagementHttpClient.Response sendCallRequest(
            String callerClientId,
            String targetClientId,
            Object requestBody) {
        Set<String> clientIds = new java.util.LinkedHashSet<>();
        clientIds.add(callerClientId);
        clientIds.add(targetClientId);
        return sendCallMutation(
                clientIds,
                "/api/call/request",
                requestBody);
    }

    MqttManagementHttpClient.Response sendCallAccept(
            String clientId, Object requestBody) {
        return sendCallMutation(
                Set.of(clientId),
                "/api/call/accept",
                requestBody);
    }

    private MqttManagementHttpClient.Response sendCallMutation(
            Set<String> clientIds,
            String path,
            Object requestBody) {
        List<MqttManagementEndpointResolver.Endpoint> endpoints =
                endpointResolver.resolve();
        if (endpoints.isEmpty()) {
            return null;
        }

        Map<String, List<MqttManagementEndpointResolver.Endpoint>> owners =
                new LinkedHashMap<>();
        clientIds.forEach(clientId ->
                owners.put(clientId, new ArrayList<>()));

        RuntimeException statusFailure = null;
        int successfulStatusBackends = 0;
        for (MqttManagementEndpointResolver.Endpoint endpoint : endpoints) {
            try {
                MqttManagementHttpClient.Response response =
                        httpClient.post(
                                endpoint,
                                "/api/devices/status",
                                Map.of("clientIds", clientIds));
                if (!response.isSuccessfulHttp()) {
                    throw new IllegalStateException(
                            "MQTT管理状态查询失败: "
                                    + response.statusCode());
                }
                Map<String, BackendDeviceStatus> statuses =
                        parseStatusResponse(response.body(), clientIds);
                owners.forEach((clientId, matches) -> {
                    if (statuses.get(clientId).exists()) {
                        matches.add(endpoint);
                    }
                });
                successfulStatusBackends++;
            } catch (RuntimeException e) {
                statusFailure = e;
            }
        }

        if (statusFailure != null
                || successfulStatusBackends != endpoints.size()) {
            throw new ManagementUnavailableException(
                    "无法确认通话设备所在的MQTT后端",
                    statusFailure);
        }

        for (Map.Entry<String, List<MqttManagementEndpointResolver.Endpoint>>
                owner : owners.entrySet()) {
            if (owner.getValue().isEmpty()) {
                return callErrorResponse(
                        endpoints.get(0).backend(),
                        404,
                        "offline",
                        "设备不在线",
                        "DEVICE_OFFLINE");
            }
            if (owner.getValue().size() > 1) {
                return callErrorResponse(
                        endpoints.get(0).backend(),
                        409,
                        "error",
                        "设备同时存在于多个MQTT后端",
                        "DEVICE_BACKEND_AMBIGUOUS");
            }
        }

        MqttManagementEndpointResolver.Endpoint selected =
                owners.values().iterator().next().get(0);
        boolean sameBackend = owners.values().stream()
                .allMatch(matches -> matches.get(0).equals(selected));
        if (!sameBackend) {
            return callErrorResponse(
                    selected.backend(),
                    409,
                    "error",
                    "跨MQTT后端通话暂不支持",
                    "CROSS_BACKEND_CALL_UNSUPPORTED");
        }
        return httpClient.post(selected, path, requestBody);
    }

    private MqttManagementHttpClient.Response sendCommand(
            MqttManagementEndpointResolver.Endpoint endpoint,
            String clientId,
            Object requestBody) {
        String encodedClientId = URLEncoder.encode(
                clientId, StandardCharsets.UTF_8)
                .replace("+", "%20");
        return httpClient.post(
                endpoint,
                "/api/commands/" + encodedClientId,
                requestBody);
    }

    private static Map<String, MutableDeviceStatus> initializeStatuses(
            Set<String> clientIds) {
        Map<String, MutableDeviceStatus> result = new LinkedHashMap<>();
        clientIds.forEach(clientId ->
                result.put(clientId, new MutableDeviceStatus()));
        return result;
    }

    private static void mergeStatusResponse(
            Map<String, MutableDeviceStatus> merged,
            MqttManagementEndpointResolver.Backend backend,
            String body) {
        Map<String, BackendDeviceStatus> response =
                parseStatusResponse(body, merged.keySet());
        merged.forEach((clientId, status) -> {
            BackendDeviceStatus value = response.get(clientId);
            status.exists |= value.exists();
            status.alive |= value.alive();
            if (value.exists()) {
                status.backends.add(
                        backend.name().toLowerCase());
            }
        });
    }

    private static Map<String, BackendDeviceStatus> parseStatusResponse(
            String body, Set<String> clientIds) {
        JSONObject response;
        try {
            response = JSONUtil.parseObj(body);
        } catch (RuntimeException e) {
            throw new IllegalStateException(
                    "MQTT管理状态响应不是JSON对象", e);
        }
        Map<String, BackendDeviceStatus> statuses =
                new LinkedHashMap<>();
        for (String clientId : clientIds) {
            Object rawStatus = response.get(clientId);
            if (!(rawStatus instanceof JSONObject status)
                    || !status.containsKey("exists")
                    || !status.containsKey("isAlive")) {
                throw new IllegalStateException(
                        "MQTT管理状态响应缺少设备状态: " + clientId);
            }
            Object rawExists = status.get("exists");
            Object rawAlive = status.get("isAlive");
            if (!(rawExists instanceof Boolean exists)
                    || !(rawAlive instanceof Boolean alive)
                    || (!exists && alive)) {
                throw new IllegalStateException(
                        "MQTT管理状态响应字段无效: " + clientId);
            }
            statuses.put(
                    clientId,
                    new BackendDeviceStatus(exists, alive));
        }
        return statuses;
    }

    private static boolean isCommandSuccess(
            MqttManagementHttpClient.Response response) {
        if (response == null || !response.isSuccessfulHttp()) {
            return false;
        }
        try {
            return JSONUtil.parseObj(response.body())
                    .getBool("success", false);
        } catch (Exception e) {
            return false;
        }
    }

    private static MqttManagementHttpClient.Response offlineResponse(
            MqttManagementEndpointResolver.Backend backend) {
        return new MqttManagementHttpClient.Response(
                backend,
                404,
                JSONUtil.toJsonStr(Map.of(
                        "success", false,
                        "error", "设备未连接",
                        "code", "DEVICE_OFFLINE",
                        "dispatchAttempted", false)));
    }

    private static MqttManagementHttpClient.Response callErrorResponse(
            MqttManagementEndpointResolver.Backend backend,
            int statusCode,
            String status,
            String message,
            String code) {
        return new MqttManagementHttpClient.Response(
                backend,
                statusCode,
                JSONUtil.toJsonStr(Map.of(
                        "status", status,
                        "message", message,
                        "code", code)));
    }

    private static MqttManagementHttpClient.Response commandErrorResponse(
            MqttManagementEndpointResolver.Backend backend,
            int statusCode,
            String error,
            String code) {
        return new MqttManagementHttpClient.Response(
                backend,
                statusCode,
                JSONUtil.toJsonStr(Map.of(
                        "success", false,
                        "error", error,
                        "code", code,
                        "dispatchAttempted", false)));
    }

    static final class ManagementUnavailableException
            extends RuntimeException {
        ManagementUnavailableException(
                String message, Throwable cause) {
            super(message, cause);
        }
    }

    private static final class MutableDeviceStatus {
        private boolean exists;
        private boolean alive;
        private final List<String> backends = new ArrayList<>();

        Map<String, Object> toMap() {
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("isAlive", alive);
            result.put("exists", exists);
            result.put("backends", backends);
            return result;
        }
    }

    private record BackendDeviceStatus(boolean exists, boolean alive) {
    }
}
