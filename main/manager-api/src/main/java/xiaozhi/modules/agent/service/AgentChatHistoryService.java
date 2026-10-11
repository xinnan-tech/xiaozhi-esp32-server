package xiaozhi.modules.agent.service;

import java.util.List;
import java.util.Map;

import com.baomidou.mybatisplus.extension.repository.IRepository;

import xiaozhi.common.page.PageData;
import xiaozhi.modules.agent.dto.AgentChatHistoryDTO;
import xiaozhi.modules.agent.dto.AgentChatSessionDTO;
import xiaozhi.modules.agent.entity.AgentChatHistoryEntity;
import xiaozhi.modules.agent.vo.AgentChatHistoryUserVO;

/**
 * Agent chat history table processing service
 *
 * @author Goody
 * @version 1.0, 2025/4/30
 * @since 1.0.0
 */
public interface AgentChatHistoryService extends IRepository<AgentChatHistoryEntity> {

    /**
     * Get session list by agent ID
     *
     * @param params Query parameters, including agentId, page, limit
     * @return Paginated session list
     */
    PageData<AgentChatSessionDTO> getSessionListByAgentId(Map<String, Object> params);

    /**
     * Get chat record list by session ID
     *
     * @param agentId   Agent ID
     * @param sessionId Session ID
     * @return Chat record list
     */
    List<AgentChatHistoryDTO> getChatHistoryBySessionId(String agentId, String sessionId);

    /**
     * Get agent ID by session ID
     *
     * @param sessionId Session ID
     * @return Agent ID
     */
    String getAgentIdBySessionId(String sessionId);

    /**
     * Delete chat records by agent ID
     *
     * @param agentId     Agent ID
     * @param deleteAudio Whether to delete audio
     * @param deleteText  Whether to delete text
     */
    void deleteByAgentId(String agentId, Boolean deleteAudio, Boolean deleteText);

    /**
     * Delete chat session by agent ID and session ID
     *
     * @param agentId   Agent ID
     * @param sessionId Session ID
     */
    void deleteBySessionId(String agentId, String sessionId);

    /**
     * Get recent 50 user chat records by agent ID (with audio data)
     *
     * @param agentId Agent ID
     * @return Chat record list (user only)
     */
    List<AgentChatHistoryUserVO> getRecentlyFiftyByAgentId(String agentId);

    /**
     * Get chat content by audio data ID
     *
     * @param audioId Audio ID
     * @return Chat content
     */
    String getContentByAudioId(String audioId);

    /**
     * Get agent ID by audio ID
     *
     * @param audioId Audio ID
     * @return Agent ID
     */
    String getAgentIdByAudioId(String audioId);


    /**
     * Check if this audio ID belongs to this agent
     *
     * @param audioId Audio ID
     * @param agentId Agent ID
     * @return T: belongs F: does not belong
     */
    boolean isAudioOwnedByAgent(String audioId,String agentId);
}
