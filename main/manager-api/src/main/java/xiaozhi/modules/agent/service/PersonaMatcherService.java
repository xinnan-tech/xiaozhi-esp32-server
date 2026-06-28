package xiaozhi.modules.agent.service;

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
}
