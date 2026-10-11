package xiaozhi.modules.timbre.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

/**
 * Timbre table data DTO
 * 
 * @author zjy
 * @since 2025-3-21
 */
@Data
@Schema(description = "Timbre Table Information")
public class TimbreDataDTO {

    @Schema(description = "Language")
    @NotBlank(message = "{timbre.languages.require}")
    private String languages;

    @Schema(description = "Timbre Name")
    @NotBlank(message = "{timbre.name.require}")
    private String name;

    @Schema(description = "Remark")
    private String remark;

    @Schema(description = "Reference Audio Path")
    private String referenceAudio;

    @Schema(description = "Reference Text")
    private String referenceText;

    @Schema(description = "Sort Order")
    @Min(value = 0, message = "{sort.number}")
    private Long sort;

    @Schema(description = "Corresponding TTS Model Primary Key")
    @NotBlank(message = "{timbre.ttsModelId.require}")
    private String ttsModelId;

    @Schema(description = "Timbre Code")
    @NotBlank(message = "{timbre.ttsVoice.require}")
    private String ttsVoice;

    @Schema(description = "Audio Playback URL")
    private String voiceDemo;
}
