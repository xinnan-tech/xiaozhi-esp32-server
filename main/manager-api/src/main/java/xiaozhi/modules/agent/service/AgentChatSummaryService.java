package xiaozhi.modules.agent.service;

/**
 * 智能体聊天记录总结服务接口
 */
public interface AgentChatSummaryService {

    /**
     * 根据会话ID生成聊天记录总结并保存到智能体记忆
     * 
     * @param sessionId 会话ID
     * @return 保存结果
     */
    boolean generateAndSaveChatSummary(String sessionId);

    /**
     * 根据会话ID生成聊天标题并保存
     *
     * @param sessionId 会话ID
     * @return 是否成功
     */
    boolean generateAndSaveChatTitle(String sessionId);
}