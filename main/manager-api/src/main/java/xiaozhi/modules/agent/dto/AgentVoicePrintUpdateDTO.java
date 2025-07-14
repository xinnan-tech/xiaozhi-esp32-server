package xiaozhi.modules.agent.dto;

import lombok.Data;

/**
 * 修改智能体声纹的dto
 *
 * @author zjy
 */
@Data
public class AgentVoicePrintUpdateDTO {
    /**
     * 智能体声纹id
     */
    private String id;
    /**
     * 音频文件id
     */
    private String audioId;
    /**
     * 声纹来源的人姓名
     */
    private String sourceName;
    /**
     * 描述声纹来源的人
     */
    private String introduce;
}
