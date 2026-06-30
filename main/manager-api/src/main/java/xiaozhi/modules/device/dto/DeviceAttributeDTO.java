package xiaozhi.modules.device.dto;

import java.io.Serializable;
import java.util.Map;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import lombok.Data;

@Data
@Schema(description = "设备属性DTO")
public class DeviceAttributeDTO implements Serializable {

    @Schema(description = "设备ID")
    @NotBlank(message = "设备ID不能为空")
    private String deviceId;

    @Schema(description = "属性key")
    @NotBlank(message = "属性key不能为空")
    @Size(max = 64, message = "属性key长度不能超过64")
    private String attrKey;

    @Schema(description = "属性值")
    @Size(max = 4096, message = "属性值长度不能超过4096")
    private String attrValue;

    private static final long serialVersionUID = 1L;
}
