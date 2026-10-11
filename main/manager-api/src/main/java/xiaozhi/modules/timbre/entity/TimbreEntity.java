package xiaozhi.modules.timbre.entity;

import java.util.Date;

import com.baomidou.mybatisplus.annotation.FieldFill;
import com.baomidou.mybatisplus.annotation.FieldStrategy;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableName;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import lombok.EqualsAndHashCode;

/**
 * Timbre table entity class
 * 
 * @author zjy
 * @since 2025-3-21
 */
@Data
@EqualsAndHashCode(callSuper = false)
@TableName("ai_tts_voice")
@Schema(description = "Timbre Information")
public class TimbreEntity {

    @Schema(description = "id")
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
    @TableField(updateStrategy = FieldStrategy.NOT_NULL)
    private Long sort;

    @Schema(description = "Corresponding TTS Model Primary Key")
    private String ttsModelId;

    @Schema(description = "Timbre Code")
    private String ttsVoice;

    @Schema(description = "Audio Playback URL")
    private String voiceDemo;

    @Schema(description = "Updater")
    @TableField(fill = FieldFill.UPDATE)
    private Long updater;

    @Schema(description = "Update Time")
    @TableField(fill = FieldFill.UPDATE)
    private Date updateDate;

    @Schema(description = "Creator")
    @TableField(fill = FieldFill.INSERT)
    private Long creator;

    @Schema(description = "Create Time")
    @TableField(fill = FieldFill.INSERT)
    private Date createDate;

}
