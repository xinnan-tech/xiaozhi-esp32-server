package xiaozhi.modules.device.service.impl;

import java.net.URI;
import java.net.URISyntaxException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Locale;

import org.apache.commons.lang3.StringUtils;

import xiaozhi.common.constant.Constant;
import xiaozhi.modules.sys.service.SysParamsService;

class MqttManagementEndpointResolver {

    enum Backend {
        NATIVE,
        GATEWAY
    }

    record Endpoint(Backend backend, String baseUrl, String signatureKey) {
    }

    private final SysParamsService sysParamsService;

    MqttManagementEndpointResolver(SysParamsService sysParamsService) {
        this.sysParamsService = sysParamsService;
    }

    List<Endpoint> resolve() {
        List<Endpoint> endpoints = new ArrayList<>(2);
        resolveNative().ifPresent(endpoints::add);
        resolveGateway().ifPresent(endpoints::add);
        return endpoints;
    }

    java.util.Optional<Endpoint> resolveNative() {
        if (!isNativeMqttEnabled()) {
            return java.util.Optional.empty();
        }
        String endpoint = normalizeHttpEndpoint(sysParamsService.getValue(
                Constant.MQTT_SERVER_MANAGER_API, true));
        String signatureKey = firstConfigured(
                sysParamsService.getValue(
                        Constant.MQTT_SERVER_MANAGER_API_SECRET, true),
                sysParamsService.getValue(
                        Constant.MQTT_SERVER_SIGNATURE_KEY, true),
                sysParamsService.getValue(
                        Constant.SERVER_MQTT_SECRET, true));
        if (endpoint == null || signatureKey == null) {
            throw new ManagementConfigurationException(
                    "原生MQTT已启用但管理端点或密钥无效");
        }
        return java.util.Optional.of(
                new Endpoint(Backend.NATIVE, endpoint, signatureKey));
    }

    java.util.Optional<Endpoint> resolveGateway() {
        String rawGateway = sysParamsService.getValue(
                Constant.SERVER_MQTT_GATEWAY, true);
        String rawEndpoint = sysParamsService.getValue(
                Constant.SERVER_MQTT_MANAGER_API, true);
        if (configured(rawGateway) == null
                && configured(rawEndpoint) == null) {
            return java.util.Optional.empty();
        }
        String endpoint = normalizeHttpEndpoint(rawEndpoint);
        String signatureKey = configured(
                sysParamsService.getValue(
                        Constant.SERVER_MQTT_SECRET, true));
        if (endpoint == null || signatureKey == null) {
            throw new ManagementConfigurationException(
                    "MQTT Gateway管理端点或密钥无效");
        }
        return java.util.Optional.of(
                new Endpoint(Backend.GATEWAY, endpoint, signatureKey));
    }

    boolean isNativeMqttEnabled() {
        String enabled = sysParamsService.getValue(
                Constant.MQTT_SERVER_ENABLED, true);
        String legacyEnabled = sysParamsService.getValue(
                Constant.SERVER_MQTT_ENABLED, true);
        boolean serverEnabled = configured(enabled) != null
                ? isTrue(enabled)
                : isTrue(legacyEnabled);

        String protocolEnabled = sysParamsService.getValue(
                Constant.PROTOCOLS_MQTT_ENABLED, true);
        String enabledProtocols = sysParamsService.getValue(
                Constant.PROTOCOLS_ENABLED, true);
        boolean enabledByProtocol = isTrue(protocolEnabled);
        if (!enabledByProtocol && StringUtils.isNotBlank(enabledProtocols)) {
            String normalized = enabledProtocols
                    .replace("[", "")
                    .replace("]", "")
                    .replace("\"", "");
            enabledByProtocol = Arrays.stream(
                    normalized.split("[;,\\s]+"))
                    .anyMatch("mqtt"::equalsIgnoreCase);
        }
        return serverEnabled && enabledByProtocol;
    }

    static String normalizeHttpEndpoint(String raw) {
        String configured = configured(raw);
        if (configured == null) {
            return null;
        }
        boolean hasScheme = configured.matches(
                "^[A-Za-z][A-Za-z0-9+.-]*://.*");
        if (hasScheme
                && !configured.matches("(?i)^https?://.*")) {
            return null;
        }
        String candidate = hasScheme ? configured : "http://" + configured;
        try {
            URI uri = new URI(candidate);
            String scheme = uri.getScheme();
            if (scheme == null
                    || (!"http".equalsIgnoreCase(scheme)
                            && !"https".equalsIgnoreCase(scheme))
                    || StringUtils.isBlank(uri.getHost())
                    || uri.getUserInfo() != null
                    || uri.getQuery() != null
                    || uri.getFragment() != null
                    || uri.getPort() == 0
                    || uri.getPort() > 65535) {
                return null;
            }
            String path = uri.getPath();
            if (path == null || "/".equals(path)) {
                path = "";
            } else {
                path = path.replaceAll("/+$", "");
            }
            return new URI(
                    scheme.toLowerCase(Locale.ROOT),
                    null,
                    uri.getHost(),
                    uri.getPort(),
                    path,
                    null,
                    null).toString();
        } catch (URISyntaxException | IllegalArgumentException e) {
            return null;
        }
    }

    private static String firstConfigured(String... values) {
        for (String value : values) {
            String normalized = configured(value);
            if (normalized != null) {
                return normalized;
            }
        }
        return null;
    }

    private static String configured(String value) {
        if (StringUtils.isBlank(value)) {
            return null;
        }
        String normalized = value.trim();
        if ("null".equalsIgnoreCase(normalized)
                || normalized.contains("你")) {
            return null;
        }
        return normalized;
    }

    private static boolean isTrue(String value) {
        return "true".equalsIgnoreCase(value) || "1".equals(value);
    }

    static final class ManagementConfigurationException
            extends RuntimeException {
        ManagementConfigurationException(String message) {
            super(message);
        }
    }
}
