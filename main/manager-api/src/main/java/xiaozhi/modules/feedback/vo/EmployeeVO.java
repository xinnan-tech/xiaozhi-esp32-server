package xiaozhi.modules.feedback.vo;

import java.io.Serializable;
import java.util.Date;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
@Schema(description = "员工信息")
public class EmployeeVO implements Serializable {

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

    @Schema(description = "创建时间")
    private Date createDate;
}
