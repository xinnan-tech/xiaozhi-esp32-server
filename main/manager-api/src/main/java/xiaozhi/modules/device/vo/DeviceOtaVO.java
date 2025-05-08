package xiaozhi.modules.device.vo;

import lombok.Data;

@Data
public class DeviceOtaVO {
    private Activation activation;
    private Mqtt mqtt;
    private ServerTime server_time;
    private Firmware firmware;
    private String error;

    @Data
    public static class Activation {
        private String code;
        private String message;

        public Activation() {
        }

        public Activation(String code, String message) {
            this.code = code;
            this.message = message;
        }
    }

    @Data
    public class Mqtt {

    }

    @Data
    public static class ServerTime {
        private Long timestamp;
        private Integer timezone_offset;

        public ServerTime() {
        }

        public ServerTime(Long timestamp, Integer timezone_offset) {
            this.timestamp = timestamp;
            this.timezone_offset = timezone_offset;
        }
    }

    @Data
    public static class Firmware {
        private String version;
        private String url;

        public Firmware() {
        }

        public Firmware(String version, String url) {
            this.version = version;
            this.url = url;
        }
    }
}
