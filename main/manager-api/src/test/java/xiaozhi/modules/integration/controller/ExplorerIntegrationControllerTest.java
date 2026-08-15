package xiaozhi.modules.integration.controller;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.mock.web.MockHttpServletRequest;

import xiaozhi.common.exception.RenException;
import xiaozhi.common.utils.JsonUtils;
import xiaozhi.modules.agent.dto.AgentCreateDTO;
import xiaozhi.modules.agent.dto.AgentUpdateDTO;
import xiaozhi.modules.agent.service.AgentService;
import xiaozhi.modules.agent.vo.AgentInfoVO;
import xiaozhi.modules.device.dto.DeviceManualAddDTO;
import xiaozhi.modules.device.service.DeviceService;
import xiaozhi.modules.device.vo.UserShowDeviceListVO;
import xiaozhi.modules.integration.dto.ExplorerAgentCreateDTO;
import xiaozhi.modules.integration.dto.ExplorerAgentUpdateDTO;
import xiaozhi.modules.integration.dto.ExplorerDeviceManualAddDTO;
import xiaozhi.modules.integration.dto.ExplorerDeviceUnbindDTO;
import xiaozhi.modules.security.integration.IntegrationCredentialFilter;
import xiaozhi.modules.security.integration.IntegrationPrincipal;

class ExplorerIntegrationControllerTest {
    @Test
    void bindAndUnbindAlwaysUseTheCredentialOwner() {
        AgentService agents = mock(AgentService.class);
        DeviceService devices = mock(DeviceService.class);
        when(agents.checkAgentOwnership("agent-1", 41L)).thenReturn(true);
        ExplorerIntegrationController controller = new ExplorerIntegrationController(agents, devices);

        controller.bindDevice("agent-1", "123456", authorizedRequest());
        ExplorerDeviceUnbindDTO unbind = new ExplorerDeviceUnbindDTO();
        unbind.setDeviceId("device-1");
        controller.unbindDevice(unbind, authorizedRequest());

        verify(devices).deviceActivation("agent-1", "123456", 41L);
        verify(devices).unbindDevice(41L, "device-1");
    }

    @Test
    void anotherOwnersAgentIsDeniedBeforeAnyDeviceMutation() {
        AgentService agents = mock(AgentService.class);
        DeviceService devices = mock(DeviceService.class);
        when(agents.checkAgentOwnership("agent-other", 41L)).thenReturn(false);
        ExplorerIntegrationController controller = new ExplorerIntegrationController(agents, devices);

        assertThrows(RenException.class,
                () -> controller.bindDevice("agent-other", "123456", authorizedRequest()));

        verify(devices, never()).deviceActivation(
                org.mockito.ArgumentMatchers.anyString(),
                org.mockito.ArgumentMatchers.anyString(),
                org.mockito.ArgumentMatchers.anyLong());
    }

    @Test
    void manualAddForwardsOnlyScopedDeviceFieldsAndServerOwnedAppVersion() {
        AgentService agents = mock(AgentService.class);
        DeviceService devices = mock(DeviceService.class);
        when(agents.checkAgentOwnership("agent-1", 41L)).thenReturn(true);
        ExplorerIntegrationController controller = new ExplorerIntegrationController(agents, devices);
        ExplorerDeviceManualAddDTO input = new ExplorerDeviceManualAddDTO();
        input.setAgentId("agent-1");
        input.setMacAddress("AA:BB:CC:DD:EE:FF");
        input.setBoard("ESP32-S3");

        controller.manualAddDevice(input, authorizedRequest());

        ArgumentCaptor<DeviceManualAddDTO> allowed = ArgumentCaptor.forClass(DeviceManualAddDTO.class);
        verify(devices).manualAddDevice(org.mockito.ArgumentMatchers.eq(41L), allowed.capture());
        assertEquals("agent-1", allowed.getValue().getAgentId());
        assertEquals("AA:BB:CC:DD:EE:FF", allowed.getValue().getMacAddress());
        assertEquals("ESP32-S3", allowed.getValue().getBoard());
        assertEquals("explorer-enrollment", allowed.getValue().getAppVersion());
    }

    @Test
    void createForwardsOnlyTheExplorerAgentNameUnderTheCredentialOwner() {
        AgentService agents = mock(AgentService.class);
        DeviceService devices = mock(DeviceService.class);
        when(agents.createAgent(org.mockito.ArgumentMatchers.any(AgentCreateDTO.class),
                org.mockito.ArgumentMatchers.eq(41L))).thenReturn("agent-created");
        ExplorerIntegrationController controller = new ExplorerIntegrationController(agents, devices);
        ExplorerAgentCreateDTO input = new ExplorerAgentCreateDTO();
        input.setAgentName("Explorer · 小探");

        var result = controller.createAgent(input, authorizedRequest());

        ArgumentCaptor<AgentCreateDTO> allowed = ArgumentCaptor.forClass(AgentCreateDTO.class);
        verify(agents).createAgent(allowed.capture(), org.mockito.ArgumentMatchers.eq(41L));
        assertEquals("Explorer · 小探", allowed.getValue().getAgentName());
        assertEquals("agent-created", result.getData());
    }

    @Test
    void updateForwardsOnlyTheFourExplorerFieldsUnderTheCredentialOwner() {
        AgentService agents = mock(AgentService.class);
        DeviceService devices = mock(DeviceService.class);
        ExplorerIntegrationController controller = new ExplorerIntegrationController(agents, devices);
        ExplorerAgentUpdateDTO input = new ExplorerAgentUpdateDTO();
        input.setAgentName("小探");
        input.setSystemPrompt("safe prompt");
        input.setTtsVoiceId("voice-1");
        input.setTtsLanguage("zh-CN");
        MockHttpServletRequest request = authorizedRequest();

        controller.updateAgent("agent-1", input, request);

        ArgumentCaptor<AgentUpdateDTO> allowed = ArgumentCaptor.forClass(AgentUpdateDTO.class);
        verify(agents).updateAgentByIdForOwner(org.mockito.ArgumentMatchers.eq("agent-1"), allowed.capture(),
                org.mockito.ArgumentMatchers.eq(41L));
        assertEquals("小探", allowed.getValue().getAgentName());
        assertEquals("safe prompt", allowed.getValue().getSystemPrompt());
        assertEquals("voice-1", allowed.getValue().getTtsVoiceId());
        assertEquals("zh-CN", allowed.getValue().getTtsLanguage());
        assertEquals(null, allowed.getValue().getLlmModelId());
        assertEquals(null, allowed.getValue().getTtsModelId());
    }

    @Test
    void deviceReadRequiresAgentOwnershipAndUsesOwnerScopedQuery() {
        AgentService agents = mock(AgentService.class);
        DeviceService devices = mock(DeviceService.class);
        when(agents.checkAgentOwnership("agent-1", 41L)).thenReturn(true);
        UserShowDeviceListVO managerDevice = new UserShowDeviceListVO();
        managerDevice.setId("device-1");
        managerDevice.setMacAddress("AA:BB:CC:DD:EE:FF");
        managerDevice.setBoard("bread-compact");
        managerDevice.setAppVersion("2.2.4");
        managerDevice.setBindUserName("must-not-leak");
        when(devices.getUserDeviceList(41L, "agent-1")).thenReturn(java.util.List.of(managerDevice));
        ExplorerIntegrationController controller = new ExplorerIntegrationController(agents, devices);

        var result = controller.listAgentDevices("agent-1", authorizedRequest());

        verify(agents).checkAgentOwnership("agent-1", 41L);
        verify(devices).getUserDeviceList(41L, "agent-1");
        assertEquals("agent-1", result.getData().get(0).agentId());
        assertFalse(JsonUtils.toJsonString(result).contains("bindUserName"));
        assertFalse(JsonUtils.toJsonString(result).contains("must-not-leak"));
    }

    @Test
    void agentReadReturnsOnlyFieldsRequiredByExplorer() {
        AgentService agents = mock(AgentService.class);
        DeviceService devices = mock(DeviceService.class);
        AgentInfoVO managerAgent = new AgentInfoVO();
        managerAgent.setId("agent-1");
        managerAgent.setUserId(41L);
        managerAgent.setAgentName("小探");
        managerAgent.setSystemPrompt("prompt");
        managerAgent.setTtsVoiceId("voice-1");
        managerAgent.setTtsLanguage("zh-CN");
        managerAgent.setLlmModelId("llm-1");
        managerAgent.setAsrModelId("asr-1");
        managerAgent.setTtsModelId("tts-1");
        when(agents.getAgentByIdForOwner("agent-1", 41L)).thenReturn(managerAgent);
        ExplorerIntegrationController controller = new ExplorerIntegrationController(agents, devices);

        var result = controller.getAgent("agent-1", authorizedRequest());

        assertEquals("小探", result.getData().agentName());
        assertEquals("llm-1", result.getData().llmModelId());
        assertFalse(JsonUtils.toJsonString(result).contains("userId"));
    }

    private MockHttpServletRequest authorizedRequest() {
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setAttribute(IntegrationCredentialFilter.PRINCIPAL_ATTRIBUTE,
                new IntegrationPrincipal("credential-1", "explorer", 41L));
        return request;
    }
}
