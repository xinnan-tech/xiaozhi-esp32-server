package xiaozhi.modules.integration.dto;

public record ExplorerDeviceView(
        String id,
        String agentId,
        String macAddress,
        String board,
        String appVersion) {
}
