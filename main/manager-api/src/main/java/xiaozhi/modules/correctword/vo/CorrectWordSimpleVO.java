package xiaozhi.modules.correctword.vo;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
@Schema(description = "替换词精简VO（设备端使用）")
public class CorrectWordSimpleVO {

    @Schema(description = "原词")
    private String sourceWord;

    @Schema(description = "替换词")
    private String targetWord;
}
