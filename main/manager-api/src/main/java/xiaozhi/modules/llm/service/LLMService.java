package xiaozhi.modules.llm.service;

/**
 * LLM服务接口
 * 支持多种大模型调用
 */
public interface LLMService {

    /**
     * 生成聊天记录总结
     * 
     * @param conversation   对话内容
     * @param promptTemplate 提示词模板
     * @return 总结结果
     */
    String generateSummary(String conversation, String promptTemplate);

    /**
     * 生成聊天记录总结（使用默认提示词）
     * 
     * @param conversation 对话内容
     * @return 总结结果
     */
    String generateSummary(String conversation);

    /**
     * 生成聊天记录总结（指定模型ID）
     * 
     * @param conversation 对话内容
     * @param modelId      模型ID
     * @return 总结结果
     */
    String generateSummaryWithModel(String conversation, String modelId);

    /**
     * 生成聊天记录总结（指定模型ID和提示词模板）
     * 
     * @param conversation   对话内容
     * @param promptTemplate 提示词模板
     * @param modelId        模型ID
     * @return 总结结果
     */
    String generateSummary(String conversation, String promptTemplate, String modelId);

    /**
     * 生成聊天记录总结（包含历史记忆合并）
     * 
     * @param conversation   对话内容
     * @param historyMemory  历史记忆
     * @param promptTemplate 提示词模板
     * @param modelId        模型ID
     * @return 总结结果
     */
    String generateSummaryWithHistory(String conversation, String historyMemory, String promptTemplate, String modelId);

    /**
     * 检查服务是否可用
     * 
     * @return 是否可用
     */
    boolean isAvailable();

    /**
     * 检查指定模型的服务是否可用
     * 
     * @param modelId 模型ID
     * @return 是否可用
     */
    boolean isAvailable(String modelId);

    /**
     * 生成会话标题
     * 
     * @param conversation 对话内容
     * @param modelId      模型ID
     * @return 标题（约15字）
     */
    String generateTitle(String conversation, String modelId);
}