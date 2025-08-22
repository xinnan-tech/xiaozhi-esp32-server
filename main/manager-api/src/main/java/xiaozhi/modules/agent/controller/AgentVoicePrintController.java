package xiaozhi.modules.agent.controller;

import java.util.List;

import org.apache.commons.lang3.StringUtils;
import org.apache.shiro.authz.annotation.RequiresPermissions;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.AllArgsConstructor;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.utils.Result;
import xiaozhi.modules.agent.dto.AgentVoicePrintSaveDTO;
import xiaozhi.modules.agent.dto.AgentVoicePrintUpdateDTO;
import xiaozhi.modules.agent.service.AgentVoicePrintService;
import xiaozhi.modules.agent.vo.AgentVoicePrintVO;
import xiaozhi.modules.security.user.SecurityUser;
import xiaozhi.modules.sys.service.SysParamsService;

@Tag(name = "Agent Voice Print Management")
@AllArgsConstructor
@RestController
@RequestMapping("/agent/voice-print")
public class AgentVoicePrintController {
    private final AgentVoicePrintService agentVoicePrintService;
    private final SysParamsService sysParamsService;

    @PostMapping
    @Operation(summary = "Create agent voice print")
    @RequiresPermissions("sys:role:normal")
    public Result<Void> save(@RequestBody @Valid AgentVoicePrintSaveDTO dto) {
        boolean b = agentVoicePrintService.insert(dto);
        if (b) {
            return new Result<>();
        }
        return new Result<Void>().error("Failed to create agent voice print");
    }

    @PutMapping
    @Operation(summary = "Update agent voice print")
    @RequiresPermissions("sys:role:normal")
    public Result<Void> update(@RequestBody @Valid AgentVoicePrintUpdateDTO dto) {
        Long userId = SecurityUser.getUserId();
        boolean b = agentVoicePrintService.update(userId, dto);
        if (b) {
            return new Result<>();
        }
        return new Result<Void>().error("Failed to update agent voice print");
    }

    @DeleteMapping("/{id}")
    @Operation(summary = "Delete agent voice print")
    @RequiresPermissions("sys:role:normal")
    public Result<Void> delete(@PathVariable String id) {
        Long userId = SecurityUser.getUserId();
        // First delete associated devices
        boolean delete = agentVoicePrintService.delete(userId, id);
        if (delete) {
            return new Result<>();
        }
        return new Result<Void>().error("Failed to delete agent voice print");
    }

    @GetMapping("/list/{id}")
    @Operation(summary = "Get user specified agent voice print list")
    @RequiresPermissions("sys:role:normal")
    public Result<List<AgentVoicePrintVO>> list(@PathVariable String id) {
        String voiceprintUrl = sysParamsService.getValue("server.voice_print", true);
        if (StringUtils.isBlank(voiceprintUrl) || "null".equals(voiceprintUrl)) {
            throw new RenException("Voice print interface not configured, please configure the voice print interface address in parameter settings (server.voice_print)");
        }
        Long userId = SecurityUser.getUserId();
        List<AgentVoicePrintVO> list = agentVoicePrintService.list(userId, id);
        return new Result<List<AgentVoicePrintVO>>().ok(list);
    }

}
