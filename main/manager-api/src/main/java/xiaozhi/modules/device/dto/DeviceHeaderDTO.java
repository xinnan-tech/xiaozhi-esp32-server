package xiaozhi.modules.device.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
@Schema(description = "设备连接头信息")
public class DeviceHeaderDTO {

    @Schema(description = "设备ID")
    private String deviceId;

    @Schema(description = "协议版本号")
    private Long protocolVersion;

    @Schema(description = "认证信息")
    private String authorization;

}