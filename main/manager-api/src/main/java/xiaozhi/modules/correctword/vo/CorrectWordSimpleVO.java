package xiaozhi.modules.correctword.vo;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
@Schema(description = "Simplified replacement-word VO (device-side)")
public class CorrectWordSimpleVO {

    @Schema(description = "Original Word")
    private String sourceWord;

    @Schema(description = "Replacement word")
    private String targetWord;
}
