package xiaozhi.modules.device.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import lombok.Getter;
import lombok.Setter;

@Data
@Schema(description = "设备OTA检测版本返回体，包含激活码要求")
public class DeviceReportRespDTO {
    @Schema(description = "服务器时间")
    private ServerTime serverTime;

    @Schema(description = "激活码")
    private Activation activation;

    @Schema(description = "错误信息")
    private String error;

    @Schema(description = "固件版本信息")
    private Firmware firmware;

    @Getter
    @Setter
    public static class Firmware {
        @Schema(description = "版本号")
        private String version;
        @Schema(description = "下载地址")
        private String url;
    }

    public static DeviceReportRespDTO createError(String message) {
        DeviceReportRespDTO resp = new DeviceReportRespDTO();
        resp.setError(message);
        return resp;
    }

    @Setter
    @Getter
    public static class Activation {
        @Schema(description = "激活码")
        private String code;

        @Schema(description = "激活码信息: 激活地址")
        private String message;

    }

    @Getter
    @Setter
    public static class ServerTime {
        @Schema(description = "时间戳")
        private Long timestamp;

        @Schema(description = "时区")
        private String timeZone;

        @Schema(description = "时区偏移量，单位为分钟")
        private Integer timezoneOffset;
    }
}
