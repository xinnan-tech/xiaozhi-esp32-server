package xiaozhi.modules.device.service.impl;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.aop.framework.ProxyFactory;

import xiaozhi.common.constant.Constant;
import xiaozhi.modules.device.dto.DeviceReportReqDTO;
import xiaozhi.modules.device.dto.DeviceReportRespDTO;
import xiaozhi.modules.device.entity.DeviceEntity;
import xiaozhi.modules.device.service.OtaService;
import xiaozhi.modules.sys.service.SysParamsService;

@DisplayName("设备自动升级回归测试")
class DeviceAutoUpdateTest {

    private static final String MAC_ADDRESS = "00:11:22:33:44:55";
    private static final String BOARD_TYPE = "test-board";
    private static final String CURRENT_VERSION = "1.0.0";

    @Test
    @DisplayName("#3299 自动升级关闭时 OTA 响应不包含固件")
    void disabledAutoUpdateOmitsFirmware() {
        OtaService otaService = mock(OtaService.class);
        DeviceServiceImpl service = proxiedService(deviceWithAutoUpdate(0), otaService);

        DeviceReportRespDTO response = service.checkDeviceActive(
                MAC_ADDRESS, MAC_ADDRESS, deviceReport());

        assertNull(response.getFirmware());
        verifyNoInteractions(otaService);
    }

    @Test
    @DisplayName("自动升级开启时继续执行固件查询")
    void enabledAutoUpdateChecksFirmware() {
        OtaService otaService = mock(OtaService.class);
        when(otaService.getLatestOta(BOARD_TYPE)).thenReturn(null);
        DeviceServiceImpl service = proxiedService(deviceWithAutoUpdate(1), otaService);

        DeviceReportRespDTO response = service.checkDeviceActive(
                MAC_ADDRESS, MAC_ADDRESS, deviceReport());

        assertNotNull(response.getFirmware());
        assertEquals(CURRENT_VERSION, response.getFirmware().getVersion());
        assertEquals(Constant.INVALID_FIRMWARE_URL, response.getFirmware().getUrl());
        verify(otaService).getLatestOta(BOARD_TYPE);
    }

    private DeviceServiceImpl proxiedService(DeviceEntity device, OtaService otaService) {
        SysParamsService sysParamsService = mock(SysParamsService.class);
        when(sysParamsService.getValue(Constant.SERVER_WEBSOCKET, true))
                .thenReturn("ws://127.0.0.1:8000/xiaozhi/v1/");
        when(sysParamsService.getValue(Constant.SERVER_AUTH_ENABLED, true)).thenReturn("false");
        when(sysParamsService.getValue(Constant.SERVER_MQTT_GATEWAY, true)).thenReturn(null);

        DeviceServiceImpl target = new DeviceServiceImpl(
                null, null, sysParamsService, null, otaService, null) {
            @Override
            public DeviceEntity getDeviceByMacAddress(String macAddress) {
                return device;
            }

            @Override
            public void updateDeviceConnectionInfo(String agentId, String deviceId, String appVersion) {
                // No-op: connection timestamps are outside this OTA decision test.
            }
        };

        ProxyFactory proxyFactory = new ProxyFactory(target);
        proxyFactory.setProxyTargetClass(true);
        proxyFactory.setExposeProxy(true);
        return (DeviceServiceImpl) proxyFactory.getProxy();
    }

    private DeviceEntity deviceWithAutoUpdate(int autoUpdate) {
        DeviceEntity device = new DeviceEntity();
        device.setId(MAC_ADDRESS);
        device.setMacAddress(MAC_ADDRESS);
        device.setBoard(BOARD_TYPE);
        device.setAutoUpdate(autoUpdate);
        return device;
    }

    private DeviceReportReqDTO deviceReport() {
        DeviceReportReqDTO.Application application = new DeviceReportReqDTO.Application();
        application.setVersion(CURRENT_VERSION);
        DeviceReportReqDTO.BoardInfo board = new DeviceReportReqDTO.BoardInfo();
        board.setType(BOARD_TYPE);

        DeviceReportReqDTO report = new DeviceReportReqDTO();
        report.setApplication(application);
        report.setBoard(board);
        return report;
    }
}
