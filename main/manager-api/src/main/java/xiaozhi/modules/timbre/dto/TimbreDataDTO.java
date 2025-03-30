package xiaozhi.modules.timbre.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

/**
 * 音色表数据DTO
 * 
 * @author zjy
 * @since 2025-3-21
 */
@Data
@Schema(description = "音色表信息")
public class TimbreDataDTO {

    @Schema(description = "语言")
    @NotBlank(message = "{timbre.languages.require}")
    private String languages;

    @Schema(description = "音色名称")
    @NotBlank(message = "{timbre.name.require}")
    private String name;

    @Schema(description = "备注")
    @NotBlank(message = "{timbre.remark.require}")
    private String remark;

    @Schema(description = "排序")
    @Min(value = 0, message = "{sort.number}")
    private long sort;

    @Schema(description = "对应 TTS 模型主键")
    @NotBlank(message = "{timbre.ttsModelId.require}")
    private String ttsModelId;

    @Schema(description = "音色编码")
    @NotBlank(message = "{timbre.ttsVoice.require}")
    private String ttsVoice;

    @Schema(description = "音频播放地址")
    @NotBlank(message = "{timbre.voiceDemo.require}")
    private String voiceDemo;
}