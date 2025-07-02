package xiaozhi.modules.device.dto;

import lombok.Data;

@Data
public class DeviceManualAddDTO {
    private String agentId;
    private String board;        // 设备型号
    private String appVersion;   // 固件版本
    private String macAddress;   // Mac地址
} 