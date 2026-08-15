package xiaozhi.modules.integration.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class ExplorerDeviceUnbindDTO {
    @NotBlank
    private String deviceId;
}
