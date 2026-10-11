package xiaozhi.modules.device.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
@Schema(description = "Update device contact permissions")
public class DeviceAddressBookPermissionDTO {

    @NotBlank(message = "MAC address cannot be empty")
    @Schema(description = "This device MAC address")
    private String macAddress;

    @NotBlank(message = "Target MAC address cannot be empty")
    @Schema(description = "Peer device MAC address")
    private String targetMac;

    @Schema(description = "Has call permission")
    private Boolean hasPermission;
}