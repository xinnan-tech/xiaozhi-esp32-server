package xiaozhi.modules.sys.vo;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

/**
 * 管理员分页展示用户的VO
 * @ zjy
 * @since 2025-3-25
 */
@Data
public class AdminPageUserVO {

    @Schema(description = "设备数量")
    private String deviceCount;

    @Schema(description = "手机号码")
    private String mobile;

    @Schema(description = "用户id")
    private String userid;
}
