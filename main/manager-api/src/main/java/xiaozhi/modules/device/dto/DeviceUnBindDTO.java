package xiaozhi.modules.device.dto;

import java.io.Serializable;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

/**
 * 设备解绑表单
 */
@Data
@Schema(description = "设备解绑表单")
public class DeviceUnBindDTO implements Serializable {

    @Schema(description = "设备ID")
    @NotBlank(message = "设备ID不能为空")
    private String deviceId;

}