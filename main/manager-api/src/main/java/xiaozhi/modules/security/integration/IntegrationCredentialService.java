package xiaozhi.modules.security.integration;

import java.util.Date;
import java.util.List;

public interface IntegrationCredentialService {
    String EXPLORER_SUBJECT = "explorer";

    CreatedIntegrationCredential createExplorerCredential(
            String name, Long ownerUserId, Date expiresAt, Long actorUserId);

    List<IntegrationCredentialView> listExplorerCredentials();

    void revokeExplorerCredential(String credentialId, Long actorUserId);

    IntegrationPrincipal authenticateExplorerCredential(String rawToken);

    void recordUse(String credentialId);

    record CreatedIntegrationCredential(IntegrationCredentialView credential, String token) {
    }

    record IntegrationCredentialView(
            String id,
            String name,
            String subject,
            Long ownerUserId,
            boolean enabled,
            Date expiresAt,
            Date lastUsedAt,
            Date revokedAt,
            Date createDate,
            Date updateDate) {
    }
}
