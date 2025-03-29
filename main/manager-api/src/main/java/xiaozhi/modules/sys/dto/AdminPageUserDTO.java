package xiaozhi.modules.sys.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

/**
 * 管理员分页用户的参数DTO
 * @author zjy
 * @since 2025-3-21
 */
@Data
@Schema(description = "音色分页参数")
public class AdminPageUserDTO {


    @Schema(description = "手机号码")
    private String mobile;

    @Schema(description = "页数")
    private String page;

    @Schema(description = "显示列数")
    private String limit;
}
