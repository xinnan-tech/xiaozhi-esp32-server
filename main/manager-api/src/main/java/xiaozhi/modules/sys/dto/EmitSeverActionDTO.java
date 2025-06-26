package xiaozhi.modules.sys.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import xiaozhi.modules.sys.enums.ServerActionEnum;

/**
 * 发送python服务端操作DTO
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class EmitSeverActionDTO
{
    @Schema(description = "目标ws地址")
    @NotEmpty(message = "目标ws地址不能为空")
    private String targetWs;

    @Schema(description = "指定操作")
    @NotNull(message = "操作不能为空")
    private ServerActionEnum action;
}
