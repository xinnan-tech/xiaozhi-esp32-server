package xiaozhi.modules.integration.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class ExplorerDeviceManualAddDTO {
    @NotBlank
    private String agentId;
    @NotBlank
    private String macAddress;
    @NotBlank
    private String board;
}
