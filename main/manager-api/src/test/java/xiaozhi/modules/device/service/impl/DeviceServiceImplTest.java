package xiaozhi.modules.device.service.impl;

import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.mockito.Mockito.doReturn;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.spy;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.mockito.MockedStatic;

import xiaozhi.common.redis.RedisUtils;
import xiaozhi.common.user.UserDetail;
import xiaozhi.modules.device.dao.DeviceDao;
import xiaozhi.modules.device.entity.DeviceEntity;
import xiaozhi.modules.device.service.DeviceAddressBookService;
import xiaozhi.modules.device.service.OtaService;
import xiaozhi.modules.security.user.SecurityUser;
import xiaozhi.modules.sys.service.SysParamsService;
import xiaozhi.modules.sys.service.SysUserUtilService;

@DisplayName("设备归属校验回归测试")
class DeviceServiceImplTest {

    private static final String MAC = "00:11:22:33:44:55";
    private static final long USER_ID = 1L;
    private static final long OTHER_USER_ID = 2L;

    @Test
    @DisplayName("设备属于当前用户时返回设备")
    void deviceOwnedByCurrentUserIsReturned() {
        DeviceEntity device = device(USER_ID);
        DeviceServiceImpl service = service();
        doReturn(device).when(service).getDeviceByMacAddress(MAC);

        try (MockedStatic<SecurityUser> securityUser = mockStatic(SecurityUser.class)) {
            securityUser.when(SecurityUser::getUser).thenReturn(user(USER_ID));

            assertSame(device, service.getOwnedDeviceByMacAddress(MAC));
        }
    }

    @Test
    @DisplayName("设备属于他人时按查不到处理")
    void deviceOwnedByAnotherUserIsHidden() {
        DeviceServiceImpl service = service();
        doReturn(device(OTHER_USER_ID)).when(service).getDeviceByMacAddress(MAC);

        try (MockedStatic<SecurityUser> securityUser = mockStatic(SecurityUser.class)) {
            securityUser.when(SecurityUser::getUser).thenReturn(user(USER_ID));

            assertNull(service.getOwnedDeviceByMacAddress(MAC));
        }
    }

    @Test
    @DisplayName("设备未登记时按查不到处理")
    void unregisteredDeviceIsHidden() {
        DeviceServiceImpl service = service();
        doReturn(null).when(service).getDeviceByMacAddress(MAC);

        try (MockedStatic<SecurityUser> securityUser = mockStatic(SecurityUser.class)) {
            securityUser.when(SecurityUser::getUser).thenReturn(user(USER_ID));

            assertNull(service.getOwnedDeviceByMacAddress(MAC));
        }
    }

    @Test
    @DisplayName("设备没有归属人时按查不到处理")
    void unboundDeviceIsHidden() {
        DeviceServiceImpl service = service();
        doReturn(device(null)).when(service).getDeviceByMacAddress(MAC);

        try (MockedStatic<SecurityUser> securityUser = mockStatic(SecurityUser.class)) {
            securityUser.when(SecurityUser::getUser).thenReturn(user(USER_ID));

            assertNull(service.getOwnedDeviceByMacAddress(MAC));
        }
    }

    @Test
    @DisplayName("没有登录用户时按查不到处理")
    void anonymousCallerGetsNothing() {
        DeviceEntity device = device(USER_ID);
        DeviceServiceImpl service = service();
        doReturn(device).when(service).getDeviceByMacAddress(MAC);

        try (MockedStatic<SecurityUser> securityUser = mockStatic(SecurityUser.class)) {
            securityUser.when(SecurityUser::getUser).thenReturn(null);

            assertNull(service.getOwnedDeviceByMacAddress(MAC));
        }
    }

    private DeviceServiceImpl service() {
        return spy(new DeviceServiceImpl(
                mock(DeviceDao.class),
                mock(SysUserUtilService.class),
                mock(SysParamsService.class),
                mock(RedisUtils.class),
                mock(OtaService.class),
                mock(DeviceAddressBookService.class)));
    }

    private DeviceEntity device(Long userId) {
        DeviceEntity entity = new DeviceEntity();
        entity.setMacAddress(MAC);
        entity.setUserId(userId);
        return entity;
    }

    private UserDetail user(long id) {
        UserDetail user = new UserDetail();
        user.setId(id);
        return user;
    }
}