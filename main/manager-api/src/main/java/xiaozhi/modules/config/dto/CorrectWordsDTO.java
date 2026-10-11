package xiaozhi.modules.config.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
@Schema(description = "Get agent replacement word DTO")
public class CorrectWordsDTO {

    @NotBlank(message = "Device MAC address cannot be empty")
    @Schema(description = "Device MAC address")
    private String macAddress;
}
