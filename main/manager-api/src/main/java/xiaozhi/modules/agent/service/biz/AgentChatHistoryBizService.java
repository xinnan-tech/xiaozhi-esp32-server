package xiaozhi.modules.agent.service.biz;

import xiaozhi.modules.agent.dto.AgentChatHistoryReportDTO;

/**
 * 智能体聊天历史业务逻辑层
 *
 * @author Goody
 * @version 1.0, 2025/4/30
 * @since 1.0.0
 */
public interface AgentChatHistoryBizService {

    /**
     * 聊天上报方法
     *
     * @param agentChatHistoryReportDTO 包含聊天上报所需信息的输入对象
     *                                  例如：设备MAC地址、文件类型、内容等
     * @return 上传结果，true表示成功，false表示失败
     */
    Boolean report(AgentChatHistoryReportDTO agentChatHistoryReportDTO);
}
