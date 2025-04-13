package xiaozhi.modules.config.dto;

import java.util.Map;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
@Schema(description = "获取智能体模型配置DTO")
public class AgentModelsDTO {
    @NotBlank(message = "密钥不能为空")
    @Schema(description = "密钥")
    private String secret;

    @NotBlank(message = "设备MAC地址不能为空")
    @Schema(description = "设备MAC地址")
    private String macAddress;

    @NotBlank(message = "客户端ID不能为空")
    @Schema(description = "客户端ID")
    private String clientId;

    @NotNull(message = "客户端已实例化的模型不能为空")
    @Schema(description = "客户端已实例化的模型")
    private Map<String, String> selectedModule;
}