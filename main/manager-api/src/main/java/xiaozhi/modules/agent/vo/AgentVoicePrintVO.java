package xiaozhi.modules.agent.vo;

import lombok.Data;

import java.util.Date;

/**
 * 展示智能体声纹列表VO
 */
@Data
public class AgentVoicePrintVO {

    /**
     * 主键id
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
    /**
     * 创建时间
     */
    private Date createDate;
}
