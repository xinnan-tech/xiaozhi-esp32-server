package xiaozhi.modules.security.integration;

import java.util.List;

import org.apache.shiro.authz.annotation.RequiresPermissions;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import xiaozhi.common.annotation.LogOperation;
import xiaozhi.common.utils.Result;
import xiaozhi.modules.security.integration.IntegrationCredentialService.CreatedIntegrationCredential;
import xiaozhi.modules.security.integration.IntegrationCredentialService.IntegrationCredentialView;
import xiaozhi.modules.security.user.SecurityUser;

@RestController
@RequestMapping("/admin/integration-credentials")
@RequiredArgsConstructor
public class IntegrationCredentialAdminController {
    private final IntegrationCredentialService credentialService;

    @GetMapping
    @RequiresPermissions("sys:role:superAdmin")
    public Result<List<IntegrationCredentialView>> list() {
        return new Result<List<IntegrationCredentialView>>()
                .ok(credentialService.listExplorerCredentials());
    }

    @PostMapping
    @RequiresPermissions("sys:role:superAdmin")
    public Result<CreatedIntegrationCredential> create(
            @RequestBody @Valid IntegrationCredentialCreateDTO dto) {
        CreatedIntegrationCredential created = credentialService.createExplorerCredential(
                dto.getName(), dto.getOwnerUserId(), dto.getExpiresAt(), SecurityUser.getUserId());
        return new Result<CreatedIntegrationCredential>().ok(created);
    }

    @PostMapping("/{credentialId}/revoke")
    @LogOperation("撤销 Explorer 集成凭据")
    @RequiresPermissions("sys:role:superAdmin")
    public Result<Void> revoke(@PathVariable String credentialId) {
        credentialService.revokeExplorerCredential(credentialId, SecurityUser.getUserId());
        return new Result<>();
    }
}
