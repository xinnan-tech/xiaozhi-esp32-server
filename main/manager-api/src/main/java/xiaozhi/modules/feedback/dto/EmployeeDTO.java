package xiaozhi.modules.feedback.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
@Schema(description = "员工信息")
public class EmployeeDTO {

    @Schema(description = "姓名")
    @NotBlank(message = "{employee.name.require}")
    private String name;

    @Schema(description = "几号(员工编号)")
    @NotNull(message = "{employee.number.require}")
    private Integer number;

    @Schema(description = "所属门店ID")
    @NotBlank(message = "{employee.storeId.require}")
    private String storeId;

    @Schema(description = "员工类型: manager/excellent/intern/normal")
    private String employeeType;
}
