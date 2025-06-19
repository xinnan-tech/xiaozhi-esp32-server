package xiaozhi.modules.device.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.util.Date;

@Data
@TableName("zy_ai_device_command")
@Schema(description = "设备指令表")
public class DeviceCommandEntity {
    @TableId(type = IdType.ASSIGN_UUID)
    @Schema(description = "主键")
    private String id;

    @Schema(description = "设备唯一标识")
    private String deviceId;

    @Schema(description = "指令类型")
    private String commandType;

    @Schema(description = "指令内容")
    private String commandContent;

    @Schema(description = "是否已执行(0未执行 1已执行)")
    private Integer isExecuted;

    @Schema(description = "创建者")
    private Long creator;

    @Schema(description = "创建时间")
    private Date createDate;

    @Schema(description = "更新者")
    private Long updater;

    @Schema(description = "更新时间")
    private Date updateDate;
}
