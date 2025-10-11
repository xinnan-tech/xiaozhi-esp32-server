package xiaozhi.modules.voiceclone.dto;

import java.util.List;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
@Schema(description = "声音克隆DTO")
public class VoiceCloneDTO {

    @Schema(description = "模型ID")
    private String modelId;

    @Schema(description = "音色ID列表")
    private List<String> voiceIds;

    @Schema(description = "用户ID")
    private Long userId;
}
