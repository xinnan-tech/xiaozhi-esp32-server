package xiaozhi.modules.integration.controller;

import java.util.List;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.utils.Result;
import xiaozhi.modules.agent.dto.AgentCreateDTO;
import xiaozhi.modules.agent.dto.AgentUpdateDTO;
import xiaozhi.modules.agent.service.AgentService;
import xiaozhi.modules.agent.vo.AgentInfoVO;
import xiaozhi.modules.device.dto.DeviceManualAddDTO;
import xiaozhi.modules.device.service.DeviceService;
import xiaozhi.modules.integration.dto.ExplorerAgentCreateDTO;
import xiaozhi.modules.integration.dto.ExplorerAgentUpdateDTO;
import xiaozhi.modules.integration.dto.ExplorerAgentView;
import xiaozhi.modules.integration.dto.ExplorerDeviceManualAddDTO;
import xiaozhi.modules.integration.dto.ExplorerDeviceUnbindDTO;
import xiaozhi.modules.integration.dto.ExplorerDeviceView;
import xiaozhi.modules.security.integration.IntegrationCredentialFilter;
import xiaozhi.modules.security.integration.IntegrationPrincipal;

@RestController
@RequestMapping("/integration/explorer")
@RequiredArgsConstructor
public class ExplorerIntegrationController {
    private final AgentService agentService;
    private final DeviceService deviceService;

    @GetMapping("/agent/{agentId}")
    public Result<ExplorerAgentView> getAgent(
            @PathVariable String agentId, HttpServletRequest request) {
        IntegrationPrincipal principal = principal(request);
        AgentInfoVO agent = agentService.getAgentByIdForOwner(agentId, principal.ownerUserId());
        return new Result<ExplorerAgentView>().ok(new ExplorerAgentView(
                agent.getId(),
                agent.getAgentName(),
                agent.getSystemPrompt(),
                agent.getTtsVoiceId(),
                agent.getTtsLanguage(),
                agent.getLlmModelId(),
                agent.getAsrModelId(),
                agent.getTtsModelId()));
    }

    @PostMapping("/agent")
    public Result<String> createAgent(
            @RequestBody @Valid ExplorerAgentCreateDTO dto, HttpServletRequest request) {
        IntegrationPrincipal principal = principal(request);
        AgentCreateDTO allowed = new AgentCreateDTO();
        allowed.setAgentName(dto.getAgentName());
        return new Result<String>().ok(agentService.createAgent(allowed, principal.ownerUserId()));
    }

    @PutMapping("/agent/{agentId}")
    public Result<Void> updateAgent(
            @PathVariable String agentId,
            @RequestBody @Valid ExplorerAgentUpdateDTO dto,
            HttpServletRequest request) {
        IntegrationPrincipal principal = principal(request);
        AgentUpdateDTO allowed = new AgentUpdateDTO();
        allowed.setAgentName(dto.getAgentName());
        allowed.setSystemPrompt(dto.getSystemPrompt());
        allowed.setTtsVoiceId(dto.getTtsVoiceId());
        allowed.setTtsLanguage(dto.getTtsLanguage());
        agentService.updateAgentByIdForOwner(agentId, allowed, principal.ownerUserId());
        return new Result<>();
    }

    @GetMapping("/device/bind/{agentId}")
    public Result<List<ExplorerDeviceView>> listAgentDevices(
            @PathVariable String agentId, HttpServletRequest request) {
        IntegrationPrincipal principal = principal(request);
        requireAgentOwner(agentId, principal.ownerUserId());
        List<ExplorerDeviceView> devices = deviceService.getUserDeviceList(principal.ownerUserId(), agentId)
                .stream()
                .map(device -> new ExplorerDeviceView(
                        device.getId(),
                        agentId,
                        device.getMacAddress(),
                        device.getBoard(),
                        device.getAppVersion()))
                .toList();
        return new Result<List<ExplorerDeviceView>>().ok(devices);
    }

    @PostMapping("/device/bind/{agentId}/{deviceCode}")
    public Result<Void> bindDevice(
            @PathVariable String agentId,
            @PathVariable String deviceCode,
            HttpServletRequest request) {
        IntegrationPrincipal principal = principal(request);
        requireAgentOwner(agentId, principal.ownerUserId());
        deviceService.deviceActivation(agentId, deviceCode, principal.ownerUserId());
        return new Result<>();
    }

    @PostMapping("/device/manual-add")
    public Result<Void> manualAddDevice(
            @RequestBody @Valid ExplorerDeviceManualAddDTO dto, HttpServletRequest request) {
        IntegrationPrincipal principal = principal(request);
        requireAgentOwner(dto.getAgentId(), principal.ownerUserId());
        DeviceManualAddDTO allowed = new DeviceManualAddDTO();
        allowed.setAgentId(dto.getAgentId());
        allowed.setMacAddress(dto.getMacAddress());
        allowed.setBoard(dto.getBoard());
        allowed.setAppVersion("explorer-enrollment");
        deviceService.manualAddDevice(principal.ownerUserId(), allowed);
        return new Result<>();
    }

    @PostMapping("/device/unbind")
    public Result<Void> unbindDevice(
            @RequestBody @Valid ExplorerDeviceUnbindDTO dto, HttpServletRequest request) {
        IntegrationPrincipal principal = principal(request);
        deviceService.unbindDevice(principal.ownerUserId(), dto.getDeviceId());
        return new Result<>();
    }

    private void requireAgentOwner(String agentId, Long ownerUserId) {
        if (!agentService.checkAgentOwnership(agentId, ownerUserId)) {
            throw new RenException(ErrorCode.NO_PERMISSION);
        }
    }

    private IntegrationPrincipal principal(HttpServletRequest request) {
        Object value = request.getAttribute(IntegrationCredentialFilter.PRINCIPAL_ATTRIBUTE);
        if (value instanceof IntegrationPrincipal principal) return principal;
        throw new RenException(ErrorCode.UNAUTHORIZED);
    }
}
