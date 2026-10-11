package xiaozhi.modules.agent.controller;

import org.apache.shiro.authz.annotation.RequiresPermissions;
import org.springdoc.core.annotations.ParameterObject;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.AllArgsConstructor;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.page.PageData;
import xiaozhi.common.user.UserDetail;
import xiaozhi.common.utils.Result;
import xiaozhi.modules.agent.dto.AgentSnapshotPageDTO;
import xiaozhi.modules.agent.dto.AgentSnapshotRestoreDTO;
import xiaozhi.modules.agent.service.AgentService;
import xiaozhi.modules.agent.service.AgentSnapshotService;
import xiaozhi.modules.agent.vo.AgentSnapshotVO;
import xiaozhi.modules.security.user.SecurityUser;

@Tag(name = "智能体快照")
@AllArgsConstructor
@RestController
@RequestMapping("/agent/{agentId}/snapshots")
public class AgentSnapshotController {
    private final AgentSnapshotService agentSnapshotService;
    private final AgentService agentService;

    @GetMapping
    @Operation(summary = "获取智能体快照列表")
    @RequiresPermissions("sys:role:normal")
    public Result<PageData<AgentSnapshotVO>> page(
            @PathVariable String agentId,
            @ParameterObject AgentSnapshotPageDTO params) {
        checkPermission(agentId);
        return new Result<PageData<AgentSnapshotVO>>().ok(agentSnapshotService.page(agentId, params));
    }

    @GetMapping("/{snapshotId}")
    @Operation(summary = "获取智能体快照详情")
    @RequiresPermissions("sys:role:normal")
    public Result<AgentSnapshotVO> getSnapshot(@PathVariable String agentId, @PathVariable String snapshotId) {
        checkPermission(agentId);
        return new Result<AgentSnapshotVO>().ok(agentSnapshotService.getSnapshot(agentId, snapshotId));
    }

    @PostMapping("/{snapshotId}/restore")
    @Operation(summary = "恢复智能体快照")
    @RequiresPermissions("sys:role:normal")
    public Result<Void> restore(@PathVariable String agentId, @PathVariable String snapshotId,
            @RequestBody @Valid AgentSnapshotRestoreDTO request) {
        checkPermission(agentId);
        agentSnapshotService.restoreSnapshot(agentId, snapshotId, request.getCurrentStateToken());
        return new Result<>();
    }

    @DeleteMapping("/{snapshotId}")
    @Operation(summary = "删除智能体历史快照")
    @RequiresPermissions("sys:role:normal")
    public Result<Void> deleteSnapshot(@PathVariable String agentId, @PathVariable String snapshotId) {
        checkPermission(agentId);
        agentSnapshotService.deleteSnapshot(agentId, snapshotId);
        return new Result<>();
    }

    private void checkPermission(String agentId) {
        UserDetail user = SecurityUser.getUser();
        if (user == null || !agentService.checkAgentPermission(agentId, user.getId())) {
            throw new RenException("没有权限访问该智能体快照");
        }
    }
}
