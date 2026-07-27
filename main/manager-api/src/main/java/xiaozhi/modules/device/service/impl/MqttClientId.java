package xiaozhi.modules.device.service.impl;

import java.util.Locale;

import org.apache.commons.lang3.StringUtils;

final class MqttClientId {

    private MqttClientId() {
    }

    static String build(String board, String macAddress) {
        String groupId = StringUtils.defaultIfBlank(
                board, "GID_default").trim().replace(":", "_");
        String deviceId = StringUtils.defaultIfBlank(macAddress, "unknown")
                .trim()
                .replace(":", "_");
        return groupId + "@@@" + deviceId + "@@@" + deviceId;
    }

    static String normalizeDeviceId(String macAddress) {
        return StringUtils.defaultIfBlank(macAddress, "unknown")
                .trim()
                .toLowerCase(Locale.ROOT)
                .replace(":", "_")
                .replace("-", "_");
    }
}
