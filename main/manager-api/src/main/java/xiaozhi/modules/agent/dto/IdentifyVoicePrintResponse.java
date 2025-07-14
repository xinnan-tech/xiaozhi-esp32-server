package xiaozhi.modules.agent.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import lombok.Data;

/**
 * 声纹识别接口返回的对象
 */
@Data
public class IdentifyVoicePrintResponse {
    /**
     * 最匹配的声纹id
     */
    @JsonProperty("speaker_id")
    private String speakerId;
    /**
     * 声纹的分数
     */
    private Double score;
}
