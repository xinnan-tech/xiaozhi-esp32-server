package xiaozhi.modules.device.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.AllArgsConstructor;
import lombok.Data;

/**
 * 设备绑定的DTO
 * 
 * @author zjy
 * @since 2025-3-28
 */
@Data
@AllArgsConstructor
@Schema(description = "设备连接头信息")
public class DeviceBindDTO {

    @Schema(description = "mac地址")
    private String macAddress;

    @Schema(description = "所属用户id")
    private Long userId;

    @Schema(description = "智能体id")
    private String agentId;

}