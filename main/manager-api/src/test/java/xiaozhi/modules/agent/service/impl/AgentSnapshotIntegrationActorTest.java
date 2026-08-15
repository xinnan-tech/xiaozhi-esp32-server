package xiaozhi.modules.agent.service.impl;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.List;

import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import xiaozhi.modules.agent.dao.AgentDao;
import xiaozhi.modules.agent.dao.AgentSnapshotDao;
import xiaozhi.modules.agent.dao.AgentTagDao;
import xiaozhi.modules.agent.entity.AgentEntity;
import xiaozhi.modules.agent.entity.AgentSnapshotEntity;
import xiaozhi.modules.agent.service.AgentContextProviderService;
import xiaozhi.modules.agent.vo.AgentInfoVO;
import xiaozhi.modules.correctword.service.CorrectWordFileService;

class AgentSnapshotIntegrationActorTest {
    @Test
    void explicitIntegrationActorIsPersistedAsSnapshotCreator() {
        AgentSnapshotDao snapshots = mock(AgentSnapshotDao.class);
        AgentDao agents = mock(AgentDao.class);
        AgentTagDao tags = mock(AgentTagDao.class);
        AgentContextProviderService contextProviders = mock(AgentContextProviderService.class);
        CorrectWordFileService correctWords = mock(CorrectWordFileService.class);
        AgentSnapshotServiceImpl service = new AgentSnapshotServiceImpl(
                snapshots, agents, tags, null, null, contextProviders, null, null, null, correctWords);
        AgentEntity locked = new AgentEntity();
        locked.setId("agent-1");
        AgentInfoVO current = new AgentInfoVO();
        current.setId("agent-1");
        current.setUserId(41L);
        current.setAgentName("Explorer agent");
        when(agents.selectByIdForUpdate("agent-1")).thenReturn(locked);
        when(agents.selectAgentInfoById("agent-1")).thenReturn(current);
        when(snapshots.selectLatestSnapshot("agent-1")).thenReturn(null);
        when(snapshots.insertWithNextVersion(any())).thenReturn(1);
        when(correctWords.getAgentCorrectWordFileIds("agent-1")).thenReturn(List.of());
        when(contextProviders.getByAgentId("agent-1")).thenReturn(null);
        when(tags.selectByAgentId("agent-1")).thenReturn(List.of());

        service.createSnapshot("agent-1", "config", 41L);

        ArgumentCaptor<AgentSnapshotEntity> inserted = ArgumentCaptor.forClass(AgentSnapshotEntity.class);
        verify(snapshots).insertWithNextVersion(inserted.capture());
        assertEquals(41L, inserted.getValue().getCreator());
    }
}
