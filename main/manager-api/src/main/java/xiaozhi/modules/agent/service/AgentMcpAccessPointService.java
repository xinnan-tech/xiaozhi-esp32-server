package xiaozhi.modules.agent.service;


import java.util.List;

/**
 * 智能体Mcp接入点处理service
 *
 * @author zjy
 */
public interface AgentMcpAccessPointService {
    /**
     * 获取智能体的mcp接入点地址
     * @param id 智能体id
     * @return mcp接入点地址
     */
   String getAgentMcpAccessAddress(String id);

    /**
     * 获取智能体的mcp接入点已有的工具列表
     * @param id 智能体id
     * @return 工具列表
     */
   List<String> getAgentMcpToolsList(String id);
}
