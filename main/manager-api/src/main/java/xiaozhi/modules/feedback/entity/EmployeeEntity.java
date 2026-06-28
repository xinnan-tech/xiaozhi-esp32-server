package xiaozhi.modules.feedback.entity;

import java.util.Date;

import com.baomidou.mybatisplus.annotation.FieldFill;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableName;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import lombok.EqualsAndHashCode;

@Data
@EqualsAndHashCode(callSuper = false)
@TableName("feedback_employee")
@Schema(description = "员工信息")
public class EmployeeEntity {

    @Schema(description = "员工ID")
    private String id;

    @Schema(description = "姓名")
    private String name;

    @Schema(description = "几号(员工编号)")
    private Integer number;

    @Schema(description = "所属门店ID")
    private String storeId;

    @Schema(description = "员工类型: manager/excellent/intern/normal")
    private String employeeType;

    @Schema(description = "状态 0禁用 1启用")
    private Integer status;

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
