package xiaozhi.modules.security.integration;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.Date;
import java.util.concurrent.atomic.AtomicReference;

import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import xiaozhi.modules.sys.entity.SysUserEntity;
import xiaozhi.modules.sys.service.SysUserService;

class IntegrationCredentialServiceImplTest {
    private static final long OWNER_USER_ID = 41L;
    private static final long ACTOR_USER_ID = 7L;

    @Test
    void createsOneTimeSecretButPersistsOnlyItsHashAndAuthenticatesAfterRestart() {
        IntegrationCredentialDao dao = mock(IntegrationCredentialDao.class);
        SysUserService users = activeUsers();
        AtomicReference<IntegrationCredentialEntity> persisted = new AtomicReference<>();
        when(dao.insert(any())).thenAnswer(invocation -> {
            persisted.set(invocation.getArgument(0));
            return 1;
        });

        IntegrationCredentialServiceImpl creatingService = new IntegrationCredentialServiceImpl(dao, users);
        IntegrationCredentialService.CreatedIntegrationCredential created = creatingService
                .createExplorerCredential("Explorer classroom", OWNER_USER_ID, null, ACTOR_USER_ID);

        IntegrationCredentialEntity row = persisted.get();
        assertNotNull(row);
        assertTrue(created.token().startsWith("xzi_" + row.getId() + "."));
        assertNotEquals(created.token(), row.getTokenHash());
        assertEquals(64, row.getTokenHash().length());
        assertFalse(row.getTokenHash().contains(created.token()));

        when(dao.selectById(row.getId())).thenReturn(row);
        IntegrationCredentialServiceImpl restartedService = new IntegrationCredentialServiceImpl(dao, users);
        IntegrationPrincipal principal = restartedService.authenticateExplorerCredential(created.token());
        assertEquals(new IntegrationPrincipal(row.getId(), "explorer", OWNER_USER_ID), principal);
        assertNull(restartedService.authenticateExplorerCredential("ordinary-manager-user-access-token"));
        assertNull(restartedService.authenticateExplorerCredential(created.token() + "tampered"));
    }

    @Test
    void revokedExpiredAndDisabledOwnerCredentialsAreRejected() {
        IntegrationCredentialDao dao = mock(IntegrationCredentialDao.class);
        SysUserService users = activeUsers();
        IntegrationCredentialServiceImpl service = new IntegrationCredentialServiceImpl(dao, users);
        ArgumentCaptor<IntegrationCredentialEntity> inserted = ArgumentCaptor.forClass(IntegrationCredentialEntity.class);
        when(dao.insert(any())).thenReturn(1);
        IntegrationCredentialService.CreatedIntegrationCredential created = service
                .createExplorerCredential("Explorer", OWNER_USER_ID, null, ACTOR_USER_ID);
        verify(dao).insert(inserted.capture());
        IntegrationCredentialEntity row = inserted.getValue();
        when(dao.selectById(row.getId())).thenReturn(row);

        service.revokeExplorerCredential(row.getId(), ACTOR_USER_ID);
        assertEquals(0, row.getEnabled());
        assertNotNull(row.getRevokedAt());
        assertNull(service.authenticateExplorerCredential(created.token()));

        row.setEnabled(1);
        row.setRevokedAt(null);
        row.setExpiresAt(new Date(System.currentTimeMillis() - 1_000));
        assertNull(service.authenticateExplorerCredential(created.token()));

        row.setExpiresAt(null);
        SysUserEntity disabled = new SysUserEntity();
        disabled.setId(OWNER_USER_ID);
        disabled.setStatus(0);
        when(users.selectById(OWNER_USER_ID)).thenReturn(disabled);
        assertNull(service.authenticateExplorerCredential(created.token()));
    }

    private SysUserService activeUsers() {
        SysUserService users = mock(SysUserService.class);
        SysUserEntity owner = new SysUserEntity();
        owner.setId(OWNER_USER_ID);
        owner.setStatus(1);
        when(users.selectById(OWNER_USER_ID)).thenReturn(owner);
        return users;
    }
}
