package xiaozhi.modules.agent.service;

import java.util.List;

import xiaozhi.modules.agent.vo.PersonaCandidateVO;

public interface PersonaMatcherService {

    /**
     * 为单个用户做一次匹配(保守:仅当另一角色置信度高出当前 Δ 才切换)。
     * 跳过 manual=1(由调用方保证)。
     *
     * @param userId     用户
     * @param days       取最近多少天聊天
     * @param limit      最多取多少条
     * @param minHistory 历史不足此数则不匹配(冷启动)
     */
    void matchForUser(Long userId, int days, int limit, int minHistory);

    /**
     * 列出全部候选角色(system_prompt 非空的全局角色池,与自动匹配同源)。
     */
    List<PersonaCandidateVO> listCandidatePersonas();

    /**
     * 对所有「有设备的非 manual 用户」各做一次匹配(seed 新用户 + 重评估已有)。
     * 遍历用户(来自设备),而非已有 assignment —— 否则空表永远 seed 不了新用户。
     */
    void matchAllNonManualUsers();
}
