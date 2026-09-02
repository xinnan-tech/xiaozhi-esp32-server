package xiaozhi.modules.agent.service.impl;

import java.util.Date;

import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;

import lombok.RequiredArgsConstructor;
import xiaozhi.modules.agent.dao.AgentChatTitleDao;
import xiaozhi.modules.agent.entity.AgentChatTitleEntity;
import xiaozhi.modules.agent.service.AgentChatTitleService;

@Service
@RequiredArgsConstructor
public class AgentChatTitleServiceImpl implements AgentChatTitleService {

    private final AgentChatTitleDao agentChatTitleDao;

    @Override
    public void saveOrUpdateTitle(String sessionId, String title) {
        if (StringUtils.isBlank(sessionId) || StringUtils.isBlank(title)) {
            return;
        }

        QueryWrapper<AgentChatTitleEntity> wrapper = new QueryWrapper<>();
        wrapper.eq("session_id", sessionId);

        AgentChatTitleEntity existing = agentChatTitleDao.selectOne(wrapper);

        if (existing != null) {
            existing.setTitle(title);
            existing.setUpdatedAt(new Date());
            agentChatTitleDao.updateById(existing);
        } else {
            AgentChatTitleEntity newEntity = AgentChatTitleEntity.builder()
                    .id(java.util.UUID.randomUUID().toString().replace("-", ""))
                    .sessionId(sessionId)
                    .title(title)
                    .createdAt(new Date())
                    .updatedAt(new Date())
                    .build();
            agentChatTitleDao.insert(newEntity);
        }
    }

    @Override
    public String getTitleBySessionId(String sessionId) {
        if (StringUtils.isBlank(sessionId)) {
            return null;
        }

        QueryWrapper<AgentChatTitleEntity> wrapper = new QueryWrapper<>();
        wrapper.eq("session_id", sessionId);

        AgentChatTitleEntity entity = agentChatTitleDao.selectOne(wrapper);
        return entity != null ? entity.getTitle() : null;
    }
}