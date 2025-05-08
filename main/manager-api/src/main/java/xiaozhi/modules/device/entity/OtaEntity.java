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
@TableName("ai_ota")
@Schema(description = "固件信息")
public class OtaEntity {

    @TableId(type = IdType.ASSIGN_UUID)
    @Schema(description = "ID")
    private String id;

    @Schema(description = "固件名称")
    private String firmwareName;

    @Schema(description = "固件类型")
    private String type;

    @Schema(description = "版本号")
    private String version;

    @Schema(description = "文件大小(字节)")
    private Long size;

    @Schema(description = "备注/说明")
    private String remark;

    @Schema(description = "固件路径")
    private String firmwarePath;

    @Schema(description = "排序")
    private Integer sort;

    @Schema(description = "更新者")
    @TableField(fill = FieldFill.UPDATE)
    private Long updater;

    @Schema(description = "更新时间")
    @TableField(fill = FieldFill.UPDATE)
    private Date updateDate;

    @Schema(description = "创建者")
    @TableField(fill = FieldFill.INSERT)
    private Long creator;

    @Schema(description = "创建时间")
    @TableField(fill = FieldFill.INSERT)
    private Date createDate;
}