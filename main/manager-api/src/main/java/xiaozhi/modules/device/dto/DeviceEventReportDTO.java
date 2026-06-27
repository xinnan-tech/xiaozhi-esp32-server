package xiaozhi.modules.device.dto;

import java.io.Serializable;
import java.util.Map;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
@Schema(description = "设备事件上报DTO")
public class DeviceEventReportDTO implements Serializable {

    @Schema(description = "设备ID（mac地址）")
    @NotBlank(message = "设备ID不能为空")
    private String deviceId;

    @Schema(description = "事件类型")
    @NotBlank(message = "事件类型不能为空")
    private String event;

    @Schema(description = "事件payload")
    private Map<String, Object> payload;

    @Schema(description = "事件时间戳")
    private Long timestamp;

    private static final long serialVersionUID = 1L;
}
