package xiaozhi.modules.agent.service;

import xiaozhi.modules.agent.entity.AgentChatTitleEntity;

public interface AgentChatTitleService {

    void saveOrUpdateTitle(String sessionId, String title);

    String getTitleBySessionId(String sessionId);
}