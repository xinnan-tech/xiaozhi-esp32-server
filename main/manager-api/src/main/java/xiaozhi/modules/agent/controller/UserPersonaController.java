package xiaozhi.modules.agent.controller;

import java.util.Map;

import org.apache.shiro.authz.annotation.RequiresPermissions;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import lombok.AllArgsConstructor;
import xiaozhi.common.utils.Result;
import xiaozhi.modules.agent.service.UserPersonaAssignmentService;
import xiaozhi.modules.security.user.SecurityUser;

@RestController
@RequestMapping("/persona")
@AllArgsConstructor
public class UserPersonaController {

    private final UserPersonaAssignmentService userPersonaAssignmentService;

    /** 家长手动切换角色(立即生效,标 manual=1,自动任务不再覆盖) */
    @PostMapping("/switch")
    @RequiresPermissions("sys:role:normal")
    public Result<Void> switchPersona(@RequestBody Map<String, String> body) {
        String agentId = body.get("agentId");
        if (agentId == null || agentId.isBlank()) {
            return new Result<Void>().error("agentId 不能为空");
        }
        Long userId = SecurityUser.getUser().getId();
        userPersonaAssignmentService.setManual(userId, agentId);
        return new Result<Void>();
    }

    /** 恢复自动匹配(manual=0) */
    @PostMapping("/auto")
    @RequiresPermissions("sys:role:normal")
    public Result<Void> resetAuto() {
        Long userId = SecurityUser.getUser().getId();
        userPersonaAssignmentService.resetAuto(userId);
        return new Result<Void>();
    }
}
