package xiaozhi.modules.agent.service.impl;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.when;

import java.util.List;

import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.test.util.ReflectionTestUtils;

import xiaozhi.modules.agent.dao.AgentDao;
import xiaozhi.modules.agent.dto.AgentUpdateDTO;
import xiaozhi.modules.agent.entity.AgentEntity;
import xiaozhi.modules.agent.service.AgentContextProviderService;
import xiaozhi.modules.agent.service.AgentSnapshotService;
import xiaozhi.modules.agent.vo.AgentInfoVO;
import xiaozhi.modules.correctword.service.CorrectWordFileService;
import xiaozhi.common.exception.RenException;

class AgentServiceIntegrationOwnerTest {
    @Test
    void ownerScopedUpdateRejectsAnotherOwnerBeforeLockingOrMutating() {
        AgentDao agentDao = mock(AgentDao.class);
        AgentServiceImpl service = new AgentServiceImpl(
                agentDao, null, null, null, null, null, null, null,
                null, null, null, null, null, null);
        AgentEntity anotherOwnersAgent = new AgentEntity();
        anotherOwnersAgent.setId("agent-1");
        anotherOwnersAgent.setUserId(99L);
        when(agentDao.selectById("agent-1")).thenReturn(anotherOwnersAgent);

        assertThrows(RenException.class,
                () -> service.updateAgentByIdForOwner("agent-1", new AgentUpdateDTO(), 41L));

        verify(agentDao, never()).selectByIdForUpdate("agent-1");
        verify(agentDao, never()).updateById(any(AgentEntity.class));
    }

    @Test
    void ownerScopedUpdateKeepsOwnershipAndAttributesSnapshotsToThatOwner() {
        AgentDao agentDao = mock(AgentDao.class);
        AgentContextProviderService contextProviders = mock(AgentContextProviderService.class);
        CorrectWordFileService correctWords = mock(CorrectWordFileService.class);
        AgentSnapshotService snapshots = mock(AgentSnapshotService.class);
        AgentServiceImpl service = new AgentServiceImpl(
                agentDao, null, null, null, null, null, null, null,
                null, null, contextProviders, null, correctWords, snapshots);
        ReflectionTestUtils.setField(service, "baseDao", agentDao);

        AgentEntity owned = new AgentEntity();
        owned.setId("agent-1");
        owned.setUserId(41L);
        AgentInfoVO current = new AgentInfoVO();
        current.setId("agent-1");
        current.setUserId(41L);
        current.setAgentName("old-name");
        when(agentDao.selectById("agent-1")).thenReturn(owned);
        when(agentDao.selectByIdForUpdate("agent-1")).thenReturn(owned);
        when(agentDao.selectAgentInfoById("agent-1")).thenReturn(current);
        when(contextProviders.getByAgentId("agent-1")).thenReturn(null);
        when(correctWords.getAgentCorrectWordFileIds("agent-1")).thenReturn(List.of());
        when(snapshots.getCurrentVersionNo("agent-1")).thenReturn(3);
        when(agentDao.updateById(any(AgentEntity.class))).thenReturn(1);
        AgentUpdateDTO update = new AgentUpdateDTO();
        update.setAgentName("new-name");

        service.updateAgentByIdForOwner("agent-1", update, 41L);

        verify(snapshots).createSnapshot("agent-1", "current", 41L);
        verify(snapshots).createSnapshot("agent-1", "config", 41L);
        ArgumentCaptor<AgentEntity> saved = ArgumentCaptor.forClass(AgentEntity.class);
        verify(agentDao).updateById(saved.capture());
        assertEquals(41L, saved.getValue().getUpdater());
        assertEquals("new-name", saved.getValue().getAgentName());
    }
}
