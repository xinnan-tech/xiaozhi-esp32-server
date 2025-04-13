package xiaozhi.modules.sys.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
@Schema(description = "配置密钥DTO")
public class ConfigSecretDTO {
    @Schema(description = "密钥")
    @NotBlank(message = "密钥不能为空")
    private String secret;
}