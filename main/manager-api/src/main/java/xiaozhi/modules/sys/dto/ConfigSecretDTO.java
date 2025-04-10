package xiaozhi.modules.sys.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
@Schema(description = "配置密钥DTO")
public class ConfigSecretDTO {
    @Schema(description = "密钥")
    private String secret;
}