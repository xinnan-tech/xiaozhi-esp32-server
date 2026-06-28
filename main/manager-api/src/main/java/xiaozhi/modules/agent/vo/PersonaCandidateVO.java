package xiaozhi.modules.agent.vo;

import lombok.Data;

/**
 * 候选角色 VO(system_prompt 非空的全局角色,与自动匹配器同源)
 */
@Data
public class PersonaCandidateVO {
    private String id;
    private String agentName;
}
