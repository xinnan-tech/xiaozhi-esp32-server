package xiaozhi.modules.agent.dto;

import lombok.Data;

/**
 * 保存智能体声纹的dto
 *
 * @author zjy
 */
@Data
public class AgentVoicePrintSaveDTO {
    /**
     * 关联的智能体id
     */
    private String agentId;
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
