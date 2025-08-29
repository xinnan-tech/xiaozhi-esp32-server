package xiaozhi.modules.agent.controller;

import java.util.List;

import org.apache.shiro.authz.annotation.RequiresPermissions;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import xiaozhi.common.user.UserDetail;
import xiaozhi.common.utils.Result;
import xiaozhi.modules.agent.service.AgentMcpAccessPointService;
import xiaozhi.modules.agent.service.AgentService;
import xiaozhi.modules.security.user.SecurityUser;

@Tag(name = "Agent MCP Access Point Management")
@RequiredArgsConstructor
@RestController
@RequestMapping("/agent/mcp")
public class AgentMcpAccessPointController {
    private final AgentMcpAccessPointService agentMcpAccessPointService;
    private final AgentService agentService;

    /**
     * 获取智能体的Mcp接入点地址
     * 
     * @param audioId 智能体id
     * @return 返回错误提醒或者Mcp接入点地址
     */
    @Operation(summary = "Get agent MCP access point address")
    @GetMapping("/address/{agentId}")
    @RequiresPermissions("sys:role:normal")
    public Result<String> getAgentMcpAccessAddress(@PathVariable("agentId") String agentId) {
        // 获取当前用户
        UserDetail user = SecurityUser.getUser();

        // 检查权限
        if (!agentService.checkAgentPermission(agentId, user.getId())) {
            return new Result<String>().error("没有权限查看该智能体的MCP接入点地址");
        }
        String agentMcpAccessAddress = agentMcpAccessPointService.getAgentMcpAccessAddress(agentId);
        if (agentMcpAccessAddress == null) {
            return new Result<String>().ok("请联系管理员进入参数管理配置mcp接入点地址");
        }
        return new Result<String>().ok(agentMcpAccessAddress);
    }

    @Operation(summary = "Get agent MCP tools list")
    @GetMapping("/tools/{agentId}")
    @RequiresPermissions("sys:role:normal")
    public Result<List<String>> getAgentMcpToolsList(@PathVariable("agentId") String agentId) {
        // 获取当前用户
        UserDetail user = SecurityUser.getUser();

        // 检查权限
        if (!agentService.checkAgentPermission(agentId, user.getId())) {
            return new Result<List<String>>().error("没有权限查看该智能体的MCP工具列表");
        }
        List<String> agentMcpToolsList = agentMcpAccessPointService.getAgentMcpToolsList(agentId);
        return new Result<List<String>>().ok(agentMcpToolsList);
    }
}
