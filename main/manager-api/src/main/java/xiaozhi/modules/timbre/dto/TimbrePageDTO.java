package xiaozhi.modules.timbre.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

/**
 * 音色分页参数DTO
 * @author zjy
 * @since 2025-3-21
 */
@Data
@Schema(description = "音色分页参数")
public class TimbrePageDTO {

    @Schema(description = "对应 TTS 模型主键")
    @NotBlank(message = "{timbre.ttsModelId.require}")
    private String ttsModelId;

    @Schema(description = "音色名称")
    private String name;

    @Schema(description = "页数")
    private String page;

    @Schema(description = "显示列数")
    private String limit;
}
