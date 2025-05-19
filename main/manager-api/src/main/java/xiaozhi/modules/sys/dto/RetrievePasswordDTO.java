package xiaozhi.modules.sys.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

import java.io.Serializable;

/**
 * 找回密码DTO
 */
@Data
@Schema(description = "找回密码")
public class RetrievePasswordDTO implements Serializable {

    @Schema(description = "手机号码")
    @NotBlank(message = "{sysuser.password.require}")
    private String phone;

    @Schema(description = "验证码")
    @NotBlank(message = "{sysuser.password.require}")
    private String code;

    @Schema(description = "新密码")
    @NotBlank(message = "{sysuser.password.require}")
    private String password;



}