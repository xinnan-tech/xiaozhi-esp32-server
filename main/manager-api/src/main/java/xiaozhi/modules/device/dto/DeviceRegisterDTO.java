package xiaozhi.modules.device.dto;

import java.io.Serializable;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Getter;
import lombok.Setter;

/**
 * 设备注册头信息
 * 
 * @author zjy
 * @since 2025-3-28
 */
@Setter
@Getter
@Schema(description = "设备注册头信息")
public class DeviceRegisterDTO implements Serializable {

    @Schema(description = "mac地址")
    private String macAddress;

}