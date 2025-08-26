package xiaozhi.modules.device.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import lombok.Getter;
import lombok.Setter;

@Data
@Schema(description = "设备OTA检测版本返回体，包含激活码要求")
public class DeviceReportRespDTO {
    @Schema(description = "服务器时间")
    private ServerTime server_time;

    @Schema(description = "激活码")
    private Activation activation;

    @Schema(description = "错误信息")
    private String error;

    @Schema(description = "固件版本信息")
    private Firmware firmware;
    
    @Schema(description = "WebSocket配置")
    private Websocket websocket;
    
    @Schema(description = "MQTT配置")
    private Mqtt mqtt_gateway;

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

        @Schema(description = "挑战码")
        private String challenge;
    }

    @Getter
    @Setter
    public static class ServerTime {
        @Schema(description = "时间戳")
        private Long timestamp;

        @Schema(description = "时区")
        private String timeZone;

        @Schema(description = "时区偏移量，单位为分钟")
        private Integer timezone_offset;
    }
    
    @Getter
    @Setter
    public static class Websocket {
        @Schema(description = "WebSocket服务器地址")
        private String url;
    }
    
    @Getter
    @Setter
    public static class Mqtt {
        @Schema(description = "MQTT服务器地址")
        private String broker;
        
        @Schema(description = "MQTT服务器端口")
        private Integer port;
        
        @Schema(description = "MQTT服务器端点")
        private String endpoint;
        
        @Schema(description = "MQTT客户端ID")
        private String client_id;
        
        @Schema(description = "MQTT用户名")
        private String username;
        
        @Schema(description = "MQTT密码")
        private String password;
        
        @Schema(description = "发布主题")
        private String publish_topic;
        
        @Schema(description = "订阅主题")
        private String subscribe_topic;
    }
}
