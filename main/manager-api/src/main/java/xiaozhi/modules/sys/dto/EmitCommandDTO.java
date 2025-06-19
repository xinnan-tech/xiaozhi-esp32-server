package xiaozhi.modules.sys.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class EmitCommandDTO {
    @NotBlank
    private String targetWs;
    @NotBlank
    private String command;
    @NotBlank
    private String deviceId;
}
