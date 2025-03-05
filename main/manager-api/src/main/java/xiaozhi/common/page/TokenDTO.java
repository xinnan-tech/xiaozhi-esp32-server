package xiaozhi.common.page;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.io.Serializable;

/**
 * 令牌信息
 *
 * @author Jack
 */
@Data
@Schema(description = "令牌信息")
public class TokenDTO implements Serializable {


    @Schema(description = "密码")
    private String token;

    @Schema(description = "过期时间")
    private int expire;

    @Schema(description = "客户端指纹")
    private String clientHash;
}
