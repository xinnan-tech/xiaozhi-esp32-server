package xiaozhi.modules.device.dto;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

import java.io.Serializable;

/**
 * 设备绑定表单
 */
@Data
@Schema(description = "设备绑定表单")
public class DeviceBindDTO implements Serializable {

    @Schema(description = "设备验证码")
    @NotBlank(message = "设备验证码不能为空")
    private String deviceCode;

    @Schema(description = "设备ID")
    @NotBlank(message = "设备ID不能为空")
    private Long deviceId;

}