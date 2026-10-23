package xiaozhi.modules.device.service.impl;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicReference;

import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.mockito.MockedStatic;

import xiaozhi.common.constant.Constant;
import xiaozhi.common.redis.RedisKeys;
import xiaozhi.common.redis.RedisUtils;
import xiaozhi.modules.device.dao.DeviceAddressBookDao;
import xiaozhi.modules.device.entity.DeviceAddressBookEntity;
import xiaozhi.modules.device.entity.DeviceEntity;
import xiaozhi.modules.device.service.DeviceService;
import xiaozhi.modules.sys.service.SysParamsService;

class DeviceAddressBookServiceImplTest {

    private static final String MAC = "00:11:22:33:44:55";
    private static final String OTHER_MAC = "00:11:22:33:44:66";

    @Test
    void newEntryUsesTheDedicatedAddressBookInsertMapping() {
        DeviceAddressBookDao addressBookDao = mock(DeviceAddressBookDao.class);
        RedisUtils redisUtils = mock(RedisUtils.class);
        DeviceService deviceService = mock(DeviceService.class);
        SysParamsService sysParamsService = mock(SysParamsService.class);
        DeviceAddressBookServiceImpl service = new DeviceAddressBookServiceImpl(
                addressBookDao, redisUtils, deviceService, sysParamsService);
        when(addressBookDao.selectOne(any())).thenReturn(null);
        when(addressBookDao.selectList(null)).thenReturn(List.of());

        service.saveOrUpdate(MAC, OTHER_MAC, "living-room", true);

        ArgumentCaptor<DeviceAddressBookEntity> entityCaptor = ArgumentCaptor.forClass(DeviceAddressBookEntity.class);
        verify(addressBookDao).insertAddressBook(entityCaptor.capture());
        DeviceAddressBookEntity entity = entityCaptor.getValue();
        assertEquals(MAC, entity.getMacAddress());
        assertEquals(OTHER_MAC, entity.getTargetMac());
        assertEquals("living-room", entity.getAlias());
        assertTrue(entity.getHasPermission());
        verify(addressBookDao, never()).insert(any(DeviceAddressBookEntity.class));
    }

    @Test
    void blankAliasOnUnregisteredTargetFallsBackToMacSuffix() {
        DeviceAddressBookDao addressBookDao = mock(DeviceAddressBookDao.class);
        RedisUtils redisUtils = mock(RedisUtils.class);
        DeviceService deviceService = mock(DeviceService.class);
        SysParamsService sysParamsService = mock(SysParamsService.class);
        DeviceAddressBookServiceImpl service = new DeviceAddressBookServiceImpl(
                addressBookDao, redisUtils, deviceService, sysParamsService);
        when(addressBookDao.selectOne(any())).thenReturn(null);
        when(addressBookDao.selectList(null)).thenReturn(List.of());
        when(deviceService.getDeviceByMacAddress(OTHER_MAC)).thenReturn(null);

        service.saveOrUpdate(MAC, OTHER_MAC, null, true);

        ArgumentCaptor<DeviceAddressBookEntity> entityCaptor = ArgumentCaptor.forClass(DeviceAddressBookEntity.class);
        verify(addressBookDao).insertAddressBook(entityCaptor.capture());
        DeviceAddressBookEntity entity = entityCaptor.getValue();
        assertNotNull(entity.getAlias());
        assertEquals("尾号为66的设备", entity.getAlias());
        assertTrue(entity.getHasPermission());
    }

    @Test
    void blankAliasOnRegisteredTargetWithoutNicknameFallsBackToMacSuffix() {
        DeviceAddressBookDao addressBookDao = mock(DeviceAddressBookDao.class);
        RedisUtils redisUtils = mock(RedisUtils.class);
        DeviceService deviceService = mock(DeviceService.class);
        SysParamsService sysParamsService = mock(SysParamsService.class);
        DeviceAddressBookServiceImpl service = new DeviceAddressBookServiceImpl(
                addressBookDao, redisUtils, deviceService, sysParamsService);
        when(addressBookDao.selectOne(any())).thenReturn(null);
        when(addressBookDao.selectList(null)).thenReturn(List.of());
        DeviceEntity registered = new DeviceEntity();
        registered.setMacAddress(OTHER_MAC);
        registered.setAlias(null);
        when(deviceService.getDeviceByMacAddress(OTHER_MAC)).thenReturn(registered);

        service.saveOrUpdate(MAC, OTHER_MAC, null, true);

        ArgumentCaptor<DeviceAddressBookEntity> entityCaptor = ArgumentCaptor.forClass(DeviceAddressBookEntity.class);
        verify(addressBookDao).insertAddressBook(entityCaptor.capture());
        assertEquals("尾号为66的设备", entityCaptor.getValue().getAlias(),
                "登记了但没起名的设备落个空名，缓存刷新会跳过这条，对方永远呼不过来");
    }

    @Test
    void callByNicknameFallsBackToMacSuffixWhenCallerHasNoAlias() {
        DeviceAddressBookDao addressBookDao = mock(DeviceAddressBookDao.class);
        RedisUtils redisUtils = mock(RedisUtils.class);
        DeviceService deviceService = mock(DeviceService.class);
        SysParamsService sysParamsService = mock(SysParamsService.class);
        DeviceAddressBookServiceImpl service = new DeviceAddressBookServiceImpl(
                addressBookDao, redisUtils, deviceService, sysParamsService);

        Map<String, Map<String, String>> books = new HashMap<>();
        Map<String, String> callerBook = new HashMap<>();
        callerBook.put("office", OTHER_MAC + "|1");
        books.put(MAC, callerBook);
        when(redisUtils.get(RedisKeys.getAddressBookKey())).thenReturn(books);
        when(deviceService.getDeviceByMacAddress(MAC)).thenReturn(null);
        when(sysParamsService.getValue("server.mqtt_manager_api", true)).thenReturn("127.0.0.1:1883");
        when(sysParamsService.getValue(Constant.SERVER_MQTT_SECRET, true)).thenReturn("gateway-key");

        // 网关是真的 http 调用，桩掉它，否则测试会往 127.0.0.1:1883 真发请求
        AtomicReference<String> sentUrl = new AtomicReference<>();
        AtomicReference<String> sentBody = new AtomicReference<>();
        Map<String, Object> result;
        try (MockedStatic<MqttGatewayAuthorization> gateway = mockStatic(MqttGatewayAuthorization.class)) {
            gateway.when(() -> MqttGatewayAuthorization.postJson(
                            anyString(), anyString(), anyString(), any(), anyInt()))
                    .thenAnswer(invocation -> {
                        sentUrl.set(invocation.getArgument(0));
                        sentBody.set(invocation.getArgument(1));
                        return "{\"status\":\"success\",\"message\":\"ok\"}";
                    });
            result = service.callByNickname(MAC, "office", false);
        }

        assertEquals("success", result.get("status"));
        assertEquals("http://127.0.0.1:1883/api/call/request", sentUrl.get());
        assertTrue(sentBody.get().contains("尾号为55的设备"),
                "主叫方没登记也没起名时该退回尾号称呼：" + sentBody.get());
    }
}