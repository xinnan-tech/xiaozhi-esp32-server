package xiaozhi.modules.device.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
@Schema(description = "更新设备通讯录权限")
public class DeviceAddressBookPermissionDTO {

    @NotBlank(message = "MAC地址不能为空")
    @Schema(description = "本设备MAC地址")
    private String macAddress;

    @NotBlank(message = "目标MAC地址不能为空")
    @Schema(description = "对方设备MAC地址")
    private String targetMac;

    @Schema(description = "是否有权限呼叫")
    private Boolean hasPermission;
}