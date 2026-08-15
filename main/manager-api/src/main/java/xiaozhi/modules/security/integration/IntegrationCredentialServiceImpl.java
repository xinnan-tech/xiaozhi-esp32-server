package xiaozhi.modules.security.integration;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.util.Base64;
import java.util.Date;
import java.util.HexFormat;
import java.util.List;
import java.util.UUID;
import java.util.regex.Pattern;

import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;
import xiaozhi.modules.sys.entity.SysUserEntity;
import xiaozhi.modules.sys.service.SysUserService;

@Service
@RequiredArgsConstructor
@Slf4j
public class IntegrationCredentialServiceImpl implements IntegrationCredentialService {
    private static final String TOKEN_PREFIX = "xzi_";
    private static final int SECRET_BYTES = 32;
    private static final SecureRandom SECURE_RANDOM = new SecureRandom();
    private static final Pattern CREDENTIAL_ID_PATTERN = Pattern.compile("[0-9a-f]{32}");
    private static final Pattern CREDENTIAL_SECRET_PATTERN = Pattern.compile("[A-Za-z0-9_-]{43}");

    private final IntegrationCredentialDao credentialDao;
    private final SysUserService sysUserService;

    @Override
    @Transactional(rollbackFor = Exception.class)
    public CreatedIntegrationCredential createExplorerCredential(
            String name, Long ownerUserId, Date expiresAt, Long actorUserId) {
        if (StringUtils.isBlank(name) || name.trim().length() > 100
                || ownerUserId == null || actorUserId == null) {
            throw new RenException(ErrorCode.PARAMS_GET_ERROR);
        }
        if (expiresAt != null && !expiresAt.after(new Date())) {
            throw new RenException(ErrorCode.PARAMS_GET_ERROR);
        }
        SysUserEntity owner = sysUserService.selectById(ownerUserId);
        if (owner == null || owner.getStatus() == null || owner.getStatus() == 0) {
            throw new RenException(ErrorCode.NO_PERMISSION);
        }

        String id = UUID.randomUUID().toString().replace("-", "");
        byte[] secret = new byte[SECRET_BYTES];
        SECURE_RANDOM.nextBytes(secret);
        String token = TOKEN_PREFIX + id + "." + Base64.getUrlEncoder().withoutPadding().encodeToString(secret);

        Date now = new Date();
        IntegrationCredentialEntity entity = new IntegrationCredentialEntity();
        entity.setId(id);
        entity.setName(name.trim());
        entity.setSubject(EXPLORER_SUBJECT);
        entity.setOwnerUserId(ownerUserId);
        entity.setTokenHash(hash(token));
        entity.setEnabled(1);
        entity.setExpiresAt(expiresAt);
        entity.setCreator(actorUserId);
        entity.setCreateDate(now);
        entity.setUpdater(actorUserId);
        entity.setUpdateDate(now);
        credentialDao.insert(entity);
        log.info("Integration credential created: subject={}, credentialId={}, ownerUserId={}, actorUserId={}",
                entity.getSubject(), entity.getId(), entity.getOwnerUserId(), actorUserId);

        return new CreatedIntegrationCredential(toView(entity), token);
    }

    @Override
    public List<IntegrationCredentialView> listExplorerCredentials() {
        return credentialDao.selectList(new LambdaQueryWrapper<IntegrationCredentialEntity>()
                .eq(IntegrationCredentialEntity::getSubject, EXPLORER_SUBJECT)
                .orderByDesc(IntegrationCredentialEntity::getCreateDate))
                .stream()
                .map(this::toView)
                .toList();
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void revokeExplorerCredential(String credentialId, Long actorUserId) {
        if (StringUtils.isBlank(credentialId) || actorUserId == null) {
            throw new RenException(ErrorCode.PARAMS_GET_ERROR);
        }
        IntegrationCredentialEntity entity = credentialDao.selectById(credentialId);
        if (entity == null || !EXPLORER_SUBJECT.equals(entity.getSubject())) {
            throw new RenException(ErrorCode.NO_PERMISSION);
        }
        Date now = new Date();
        entity.setEnabled(0);
        entity.setRevokedAt(now);
        entity.setUpdater(actorUserId);
        entity.setUpdateDate(now);
        credentialDao.updateById(entity);
        log.info("Integration credential revoked: subject={}, credentialId={}, ownerUserId={}, actorUserId={}",
                entity.getSubject(), entity.getId(), entity.getOwnerUserId(), actorUserId);
    }

    @Override
    public IntegrationPrincipal authenticateExplorerCredential(String rawToken) {
        String credentialId = credentialId(rawToken);
        if (credentialId == null) return null;

        IntegrationCredentialEntity entity = credentialDao.selectById(credentialId);
        Date now = new Date();
        if (entity == null
                || !EXPLORER_SUBJECT.equals(entity.getSubject())
                || entity.getEnabled() == null
                || entity.getEnabled() != 1
                || (entity.getExpiresAt() != null && !entity.getExpiresAt().after(now))
                || StringUtils.isBlank(entity.getTokenHash())
                || !MessageDigest.isEqual(
                        entity.getTokenHash().getBytes(StandardCharsets.US_ASCII),
                        hash(rawToken).getBytes(StandardCharsets.US_ASCII))) {
            return null;
        }

        SysUserEntity owner = sysUserService.selectById(entity.getOwnerUserId());
        if (owner == null || owner.getStatus() == null || owner.getStatus() == 0) return null;
        return new IntegrationPrincipal(entity.getId(), entity.getSubject(), entity.getOwnerUserId());
    }

    @Override
    public void recordUse(String credentialId) {
        IntegrationCredentialEntity entity = new IntegrationCredentialEntity();
        entity.setId(credentialId);
        entity.setLastUsedAt(new Date());
        entity.setUpdateDate(new Date());
        credentialDao.updateById(entity);
    }

    private String credentialId(String rawToken) {
        if (StringUtils.isBlank(rawToken) || !rawToken.startsWith(TOKEN_PREFIX)) return null;
        int separator = rawToken.indexOf('.', TOKEN_PREFIX.length());
        if (separator < 0) return null;
        String id = rawToken.substring(TOKEN_PREFIX.length(), separator);
        if (!CREDENTIAL_ID_PATTERN.matcher(id).matches()) return null;
        String secret = rawToken.substring(separator + 1);
        return CREDENTIAL_SECRET_PATTERN.matcher(secret).matches() ? id : null;
    }

    private String hash(String rawToken) {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256")
                    .digest(rawToken.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(digest);
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException("SHA-256 is unavailable", exception);
        }
    }

    private IntegrationCredentialView toView(IntegrationCredentialEntity entity) {
        return new IntegrationCredentialView(
                entity.getId(),
                entity.getName(),
                entity.getSubject(),
                entity.getOwnerUserId(),
                Integer.valueOf(1).equals(entity.getEnabled()),
                entity.getExpiresAt(),
                entity.getLastUsedAt(),
                entity.getRevokedAt(),
                entity.getCreateDate(),
                entity.getUpdateDate());
    }
}
