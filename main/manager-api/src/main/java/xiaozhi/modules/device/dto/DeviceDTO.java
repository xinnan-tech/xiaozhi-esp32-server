package xiaozhi.modules.device.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import java.util.Date;

@Data
@Schema(description = "设备信息")
public class DeviceDTO {
    @Schema(description = "设备ID")
    private Long id;

    @Schema(description = "关联用户ID")
    private Long userId;

    @Schema(description = "MAC地址")
    private String macAddress;

    @Schema(description = "最后连接时间")
    private Date lastConnectedAt;

    @Schema(description = "自动更新开关(0关闭/1开启)")
    private Integer autoUpdate;

    @Schema(description = "设备硬件型号")
    private String board;

    @Schema(description = "设备别名")
    private String alias;

    @Schema(description = "智能体编码")
    private String agentCode;

    @Schema(description = "智能体ID")
    private Long agentId;

    @Schema(description = "固件版本号")
    private String appVersion;

    @Schema(description = "排序")
    private Integer sort;

    @Schema(description = "创建者")
    private Long creator;

    @Schema(description = "创建时间")
    private Date createDate;

    @Schema(description = "更新者")
    private Long updater;

    @Schema(description = "更新时间")
    private Date updateDate;

    @Schema(description = "设备编码")
    private String deviceCode;  
}