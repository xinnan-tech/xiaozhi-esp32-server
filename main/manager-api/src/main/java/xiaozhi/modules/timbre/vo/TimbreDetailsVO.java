package xiaozhi.modules.timbre.vo;

import java.io.Serializable;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

/**
 * Timbre details display VO
 * 
 * @author zjy
 * @since 2025-3-21
 */
@Data
public class TimbreDetailsVO implements Serializable {
    @Schema(description = "Timbre ID")
    private String id;

    @Schema(description = "Language")
    private String languages;

    @Schema(description = "Timbre Name")
    private String name;

    @Schema(description = "Remark")
    private String remark;

    @Schema(description = "Reference Audio Path")
    private String referenceAudio;

    @Schema(description = "Reference Text")
    private String referenceText;

    @Schema(description = "Sort Order")
    private Long sort;

    @Schema(description = "Corresponding TTS Model Primary Key")
    private String ttsModelId;

    @Schema(description = "Timbre Code")
    private String ttsVoice;

    @Schema(description = "Audio Playback URL")
    private String voiceDemo;

}
