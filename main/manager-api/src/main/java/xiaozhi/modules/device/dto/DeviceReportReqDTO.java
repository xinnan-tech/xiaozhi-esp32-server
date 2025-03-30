package xiaozhi.modules.device.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Getter;
import lombok.Setter;

import java.io.Serializable;
import java.util.List;

@Setter
@Getter
@Schema(description = "设备固件信息上报求请求体")
public class DeviceReportReqDTO implements Serializable {
    private static final long serialVersionUID = 1L;
    // region 实体属性
    @Schema(description = "板子固件版本号")
    private Integer version;

    @Schema(description = "闪存大小（单位：字节）")
    @JsonProperty("flash_size")
    private Integer flashSize;

    @Schema(description = "最小空闲堆内存（字节）")
    @JsonProperty("minimum_free_heap_size")
    private Integer minimumFreeHeapSize;

    @Schema(description = "设备 MAC 地址")
    @JsonProperty("mac_address")
    private String macAddress;

    @Schema(description = "设备唯一标识 UUID")
    private String uuid;

    @Schema(description = "芯片型号名称")
    @JsonProperty("chip_model_name")
    private String chipModelName;

    @Schema(description = "芯片详细信息")
    @JsonProperty("chip_info")
    private ChipInfo chipInfo;

    @Schema(description = "应用程序信息")
    private Application application;

    @Schema(description = "分区表列表")
    @JsonProperty("partition_table")
    private List<Partition> partitionTable;

    @Schema(description = "当前运行的 OTA 分区信息")
    private OtaInfo ota;

    @Schema(description = "板子配置信息")
    private BoardInfo board;

    // endregion

    @Getter
    @Setter
    @Schema(description = "芯片信息")
    public static class ChipInfo {
        @Schema(description = "芯片模型代码")
        private Integer model;

        @Schema(description = "核心数")
        private Integer cores;

        @Schema(description = "硬件修订版本")
        private Integer revision;

        @Schema(description = "芯片功能标志位")
        private Integer features;
    }

    @Getter
    @Setter
    @Schema(description = "板子编译信息")
    public static class Application {
        @Schema(description = "名称")
        private String name;

        @Schema(description = "应用版本号")
        private String version;

        @Schema(description = "编译时间（UTC ISO格式）")
        @JsonProperty("compile_time")
        private String compileTime;

        @Schema(description = "ESP-IDF 版本号")
        @JsonProperty("idf_version")
        private String idfVersion;

        @Schema(description = "ELF 文件 SHA256 校验")
        @JsonProperty("elf_sha256")
        private String elfSha256;
    }

    @Getter
    @Setter
    @Schema(description = "分区信息")
    public static class Partition {
        @Schema(description = "分区标签名")
        private String label;

        @Schema(description = "分区类型")
        private Integer type;

        @Schema(description = "子类型")
        private Integer subtype;

        @Schema(description = "起始地址")
        private Integer address;

        @Schema(description = "分区大小")
        private Integer size;
    }

    @Getter
    @Setter
    @Schema(description = "OTA信息")
    public static class OtaInfo {
        @Schema(description = "当前OTA标签")
        private String label;
    }

    @Getter
    @Setter
    @Schema(description = "板子连接和网络信息")
    public static class BoardInfo {
        @Schema(description = "板子类型")
        private String type;

        @Schema(description = "连接的 Wi-Fi SSID")
        private String ssid;

        @Schema(description = "Wi-Fi 信号强度（RSSI）")
        private Integer rssi;

        @Schema(description = "Wi-Fi 信道")
        private Integer channel;

        @Schema(description = "IP 地址")
        private String ip;

        @Schema(description = "MAC 地址")
        private String mac;
    }
}
