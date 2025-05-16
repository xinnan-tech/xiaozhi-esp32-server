package xiaozhi.modules.sys.dto;

import java.io.Serializable;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

/**
 * 修改密码
 */
@Data
@Schema(description = "修改密码")
public class PasswordDTO implements Serializable {

    @Schema(description = "原密码")
    @NotBlank(message = "{sysuser.password.require}")
    private String password;

    @Schema(description = "新密码")
    @NotBlank(message = "{sysuser.password.require}")
    private String newPassword;

}