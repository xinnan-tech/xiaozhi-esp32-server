package xiaozhi.modules.agent.controller;

import java.util.Map;

import org.apache.shiro.authz.annotation.RequiresPermissions;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import cn.hutool.json.JSONUtil;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.AllArgsConstructor;
import xiaozhi.common.utils.Result;
import xiaozhi.modules.agent.entity.AgentExtEntity;
import xiaozhi.modules.agent.service.AgentExtService;

@Tag(name = "agent 扩展字段")
@RestController
@RequestMapping("/agent")
@AllArgsConstructor
public class AgentExtController {

    private final AgentExtService agentExtService;

    @GetMapping("/{id}/ext")
    @Operation(summary = "取 agent 扩展字段(JSON 对象)")
    @RequiresPermissions("sys:role:normal")
    public Result<Object> getExt(@PathVariable String id) {
        AgentExtEntity e = agentExtService.getByAgentId(id);
        Object obj = (e != null && e.getExtJson() != null && !e.getExtJson().isBlank())
                ? JSONUtil.parseObj(e.getExtJson())
                : JSONUtil.parseObj("{}");
        return new Result<>().ok(obj);
    }

    @PutMapping("/{id}/ext")
    @Operation(summary = "整体覆盖 agent 扩展字段(body=JSON 对象)")
    @RequiresPermissions("sys:role:normal")
    public Result<Void> saveExt(@PathVariable String id, @RequestBody Map<String, Object> body) {
        agentExtService.saveOrUpdate(id, JSONUtil.toJsonStr(body));
        return new Result<>();
    }
}
