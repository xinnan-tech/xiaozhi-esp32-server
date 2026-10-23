package xiaozhi.modules.device.service.impl;

import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.List;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.mockito.MockedStatic;

import com.baomidou.mybatisplus.core.conditions.update.UpdateWrapper;

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
        DeviceServiceImpl service = serviceWithDeviceDao(daoReturning(device));

        try (MockedStatic<SecurityUser> securityUser = mockStatic(SecurityUser.class)) {
            securityUser.when(SecurityUser::getUser).thenReturn(user(USER_ID));

            assertSame(device, service.getOwnedDeviceByMacAddress(MAC));
        }
    }

    @Test
    @DisplayName("设备属于他人时按查不到处理")
    void deviceOwnedByAnotherUserIsHidden() {
        DeviceServiceImpl service = serviceWithDeviceDao(daoReturning(device(OTHER_USER_ID)));

        try (MockedStatic<SecurityUser> securityUser = mockStatic(SecurityUser.class)) {
            securityUser.when(SecurityUser::getUser).thenReturn(user(USER_ID));

            assertNull(service.getOwnedDeviceByMacAddress(MAC));
        }
    }

    @Test
    @DisplayName("设备未登记时按查不到处理")
    void unregisteredDeviceIsHidden() {
        DeviceServiceImpl service = serviceWithDeviceDao(daoReturning(List.of()));

        try (MockedStatic<SecurityUser> securityUser = mockStatic(SecurityUser.class)) {
            securityUser.when(SecurityUser::getUser).thenReturn(user(USER_ID));

            assertNull(service.getOwnedDeviceByMacAddress(MAC));
        }
    }

    @Test
    @DisplayName("设备没有归属人时按查不到处理")
    void unboundDeviceIsHidden() {
        DeviceServiceImpl service = serviceWithDeviceDao(daoReturning(device(null)));

        try (MockedStatic<SecurityUser> securityUser = mockStatic(SecurityUser.class)) {
            securityUser.when(SecurityUser::getUser).thenReturn(user(USER_ID));

            assertNull(service.getOwnedDeviceByMacAddress(MAC));
        }
    }

    @Test
    @DisplayName("没有登录用户时按查不到处理")
    void anonymousCallerGetsNothing() {
        DeviceServiceImpl service = serviceWithDeviceDao(daoReturning(device(USER_ID)));

        // 匿名调用的实际形态：getUser() 返回空对象，id 是空的，不是返回 null
        try (MockedStatic<SecurityUser> securityUser = mockStatic(SecurityUser.class)) {
            securityUser.when(SecurityUser::getUser).thenReturn(new UserDetail());

            assertNull(service.getOwnedDeviceByMacAddress(MAC));
        }
    }

    @Test
    @DisplayName("库里同一 MAC 有两行只差大小写时，取第一条做归属校验，不再抛异常")
    void duplicateMacDifferingOnlyInCaseStillReturnsTheDevice() {
        DeviceEntity first = device(USER_ID, "device-1");
        DeviceEntity second = device(USER_ID, "device-2");
        DeviceServiceImpl service = serviceWithDeviceDao(daoReturning(List.of(first, second)));

        try (MockedStatic<SecurityUser> securityUser = mockStatic(SecurityUser.class)) {
            securityUser.when(SecurityUser::getUser).thenReturn(user(USER_ID));

            assertSame(first, service.getOwnedDeviceByMacAddress(MAC));
        }
    }

    @Test
    @DisplayName("解绑自己的设备时，通讯录跟着一起清")
    void unbindOwnDeviceClearsItsAddressBook() {
        DeviceDao dao = mock(DeviceDao.class);
        when(dao.selectById("device-1")).thenReturn(device(USER_ID, "device-1"));
        DeviceAddressBookService addressBookService = mock(DeviceAddressBookService.class);
        DeviceServiceImpl service = serviceWithDao(dao, addressBookService);

        service.unbindDevice(USER_ID, "device-1");

        verify(dao).delete(any(UpdateWrapper.class));
        verify(addressBookService).deleteByMacAddresses(List.of(MAC));
    }

    @Test
    @DisplayName("解绑别人的设备时什么都不删，通讯录不能跟着没")
    void unbindAnotherUsersDeviceDeletesNothing() {
        DeviceDao dao = mock(DeviceDao.class);
        when(dao.selectById("device-1")).thenReturn(device(OTHER_USER_ID, "device-1"));
        DeviceAddressBookService addressBookService = mock(DeviceAddressBookService.class);
        DeviceServiceImpl service = serviceWithDao(dao, addressBookService);

        service.unbindDevice(USER_ID, "device-1");

        verify(dao, never()).delete(any(UpdateWrapper.class));
        verify(addressBookService, never()).deleteByMacAddresses(anyList());
    }

    private DeviceServiceImpl serviceWithDao(DeviceDao dao, DeviceAddressBookService addressBookService) {
        // baseDao 由父类持有，子类内部赋给 this，测试类自己碰不到它
        return new DeviceServiceImpl(
                dao, mock(SysUserUtilService.class), mock(SysParamsService.class),
                mock(RedisUtils.class), mock(OtaService.class), addressBookService) {
            {
                this.baseDao = dao;
            }
        };
    }

    private DeviceServiceImpl serviceWithDeviceDao(DeviceDao dao) {
        return serviceWithDao(dao, mock(DeviceAddressBookService.class));
    }

    private DeviceDao daoReturning(DeviceEntity device) {
        return daoReturning(List.of(device));
    }

    private DeviceDao daoReturning(List<DeviceEntity> rows) {
        DeviceDao dao = mock(DeviceDao.class);
        when(dao.selectList(any())).thenReturn(rows);
        return dao;
    }

    private DeviceEntity device(Long userId) {
        return device(userId, null);
    }

    private DeviceEntity device(Long userId, String id) {
        DeviceEntity entity = new DeviceEntity();
        entity.setId(id);
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
