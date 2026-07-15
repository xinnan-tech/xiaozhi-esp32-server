package xiaozhi.modules.device.entity;

import java.util.Date;

import com.baomidou.mybatisplus.annotation.FieldFill;
import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import lombok.EqualsAndHashCode;

@Data
@EqualsAndHashCode(callSuper = false)
@TableName("ai_device_ext")
@Schema(description = "设备扩展字段(孩子信息+家长期望)")
public class DeviceExtEntity {

    @TableId(type = IdType.INPUT)
    @Schema(description = "关联设备(主键,即 device.id)")
    private String deviceId;

    @Schema(description = "设备扩展字段 JSON {childAgeRange,childPersonality,parentGoals,parentConcerns,contentPreference}")
    private String extJson;

    @TableField(fill = FieldFill.INSERT)
    private Long creator;

    @TableField(fill = FieldFill.INSERT)
    private Date createDate;

    @TableField(fill = FieldFill.UPDATE)
    private Long updater;

    @TableField(fill = FieldFill.UPDATE)
    private Date updateDate;
}
