package xiaozhi.modules.device.dto;

import java.io.Serializable;
import java.util.Map;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
@Schema(description = "设备属性批量保存DTO")
public class DeviceAttributeBatchDTO implements Serializable {

    @Schema(description = "设备ID")
    @NotBlank(message = "设备ID不能为空")
    private String deviceId;

    @Schema(description = "属性映射")
    @NotNull(message = "属性不能为空")
    private Map<String, String> attributes;

    private static final long serialVersionUID = 1L;
}
