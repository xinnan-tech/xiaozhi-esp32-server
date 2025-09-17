package xiaozhi.modules.device.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
public class CameraStreamStartDTO {
    @Schema(description = "帧率(1-15)")
    private Integer fps;

    @Schema(description = "JPEG质量(5-30)")
    private Integer quality;
}


