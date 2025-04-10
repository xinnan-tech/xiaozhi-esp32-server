package xiaozhi.modules.timbre.vo;

import java.io.Serializable;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

/**
 * 音色详情展示VO
 * 
 * @author zjy
 * @since 2025-3-21
 */
@Data
public class TimbreDetailsVO implements Serializable {
    @Schema(description = "音色id")
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

}
