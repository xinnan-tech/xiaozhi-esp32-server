package xiaozhi.modules.timbre.entity;

import java.util.Date;

import com.baomidou.mybatisplus.annotation.FieldFill;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableName;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import lombok.EqualsAndHashCode;

/**
 * 音色表实体类
 * 
 * @author zjy
 * @since 2025-3-21
 */
@Data
@EqualsAndHashCode(callSuper = false)
@TableName("ai_tts_voice")
@Schema(description = "音色信息")
public class TimbreEntity {

    @Schema(description = "id")
    private String id;

    @Schema(description = "语言")
    private String languages;

    @Schema(description = "音色名称")
    private String name;

    @Schema(description = "备注")
    private String remark;

    @Schema(description = "排序")
    private long sort;

    @Schema(description = "对应 TTS 模型主键")
    private String ttsModelId;

    @Schema(description = "音色编码")
    private String ttsVoice;

    @Schema(description = "音频播放地址")
    private String voiceDemo;

    @Schema(description = "更新者")
    @TableField(fill = FieldFill.UPDATE)
    private Long updater;

    @Schema(description = "更新时间")
    @TableField(fill = FieldFill.UPDATE)
    private Date updateDate;

    @Schema(description = "创建者")
    @TableField(fill = FieldFill.INSERT)
    private Long creator;

    @Schema(description = "创建时间")
    @TableField(fill = FieldFill.INSERT)
    private Date createDate;

}