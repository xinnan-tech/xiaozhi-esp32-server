package xiaozhi.modules.device.controller;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.List;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.mockito.MockedStatic;

import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.redis.RedisUtils;
import xiaozhi.common.user.UserDetail;
import xiaozhi.common.utils.MessageUtils;
import xiaozhi.common.utils.Result;
import xiaozhi.modules.device.dto.DeviceAddressBookAliasDTO;
import xiaozhi.modules.device.dto.DeviceAddressBookPermissionDTO;
import xiaozhi.modules.device.dto.DeviceUpdateDTO;
import xiaozhi.modules.device.entity.DeviceAddressBookEntity;
import xiaozhi.modules.device.entity.DeviceEntity;
import xiaozhi.modules.device.service.DeviceAddressBookService;
import xiaozhi.modules.device.service.DeviceService;
import xiaozhi.modules.security.user.SecurityUser;
import xiaozhi.modules.sys.service.SysParamsService;

@DisplayName("设备更新接口回归测试")
class DeviceControllerTest {

    private static final String DEVICE_ID = "device-id";
    private static final String MAC = "00:11:22:33:44:55";
    private static final String OTHER_MAC = "00:11:22:33:44:66";
    private static final long USER_ID = 1L;

    @Test
    @DisplayName("数据库未更新时不误报自动升级状态修改成功")
    void updateFailureIsReturnedToCaller() {
        DeviceService deviceService = mock(DeviceService.class);
        DeviceEntity entity = ownedDevice();
        when(deviceService.selectById(DEVICE_ID)).thenReturn(entity);
        when(deviceService.updateById(entity)).thenReturn(false);
        DeviceController controller = controller(deviceService, mock(DeviceAddressBookService.class));

        DeviceUpdateDTO update = new DeviceUpdateDTO();
        update.setAutoUpdate(0);

        try (MockedStatic<SecurityUser> securityUser = mockStatic(SecurityUser.class);
                MockedStatic<MessageUtils> messageUtils = mockStatic(MessageUtils.class)) {
            securityUser.when(SecurityUser::getUser).thenReturn(currentUser());
            messageUtils.when(() -> MessageUtils.getMessage(ErrorCode.UPDATE_DATA_FAILED))
                    .thenReturn("Failed to update data");

            Result<Void> result = controller.updateDeviceInfo(DEVICE_ID, update);

            assertEquals(ErrorCode.UPDATE_DATA_FAILED, result.getCode());
            assertEquals(0, entity.getAutoUpdate());
            verify(deviceService).updateById(entity);
        }
    }

    @Test
    @DisplayName("读取他人设备通讯录时一律按设备不存在处理")
    void addressBookOfDeviceOwnedByAnotherUserIsRejected() {
        DeviceService deviceService = mock(DeviceService.class);
        DeviceAddressBookService addressBookService = mock(DeviceAddressBookService.class);
        when(deviceService.getOwnedDeviceByMacAddress(OTHER_MAC)).thenReturn(null);
        DeviceController controller = controller(deviceService, addressBookService);

        try (MockedStatic<MessageUtils> messageUtils = mockStatic(MessageUtils.class)) {
            messageUtils.when(() -> MessageUtils.getMessage(ErrorCode.DEVICE_NOT_EXIST))
                    .thenReturn("Device not exist");

            Result<Object> result = controller.getAddressBook(OTHER_MAC);

            assertEquals(ErrorCode.DEVICE_NOT_EXIST, result.getCode());
            assertNull(result.getData());
            verify(addressBookService, never()).getAddressBookList(OTHER_MAC);
        }
    }

    @Test
    @DisplayName("读取本机设备通讯录照常返回")
    void addressBookOfOwnDeviceIsReturned() {
        DeviceService deviceService = mock(DeviceService.class);
        DeviceAddressBookService addressBookService = mock(DeviceAddressBookService.class);
        List<DeviceAddressBookEntity> entries = List.of(new DeviceAddressBookEntity());
        when(deviceService.getOwnedDeviceByMacAddress(MAC)).thenReturn(ownedDevice());
        when(addressBookService.getAddressBookList(MAC)).thenReturn(entries);
        DeviceController controller = controller(deviceService, addressBookService);

        Result<Object> result = controller.getAddressBook(MAC);

        assertEquals(0, result.getCode());
        assertEquals(entries, result.getData());
    }

    @Test
    @DisplayName("以他人设备名义改别名被拒")
    void updateAliasOnDeviceOwnedByAnotherUserIsRejected() {
        DeviceService deviceService = mock(DeviceService.class);
        DeviceAddressBookService addressBookService = mock(DeviceAddressBookService.class);
        when(deviceService.getOwnedDeviceByMacAddress(OTHER_MAC)).thenReturn(null);
        DeviceController controller = controller(deviceService, addressBookService);

        DeviceAddressBookAliasDTO dto = new DeviceAddressBookAliasDTO();
        dto.setMacAddress(OTHER_MAC);
        dto.setTargetMac(MAC);
        dto.setAlias("office");

        Result<Void> result = controller.updateAlias(dto);

        assertEquals("无权限操作该设备", result.getMsg());
        verify(addressBookService, never()).saveOrUpdate(OTHER_MAC, MAC, "office", null);
    }

    @Test
    @DisplayName("以他人设备名义改权限被拒")
    void updatePermissionOnDeviceOwnedByAnotherUserIsRejected() {
        DeviceService deviceService = mock(DeviceService.class);
        DeviceAddressBookService addressBookService = mock(DeviceAddressBookService.class);
        when(deviceService.getOwnedDeviceByMacAddress(OTHER_MAC)).thenReturn(null);
        DeviceController controller = controller(deviceService, addressBookService);

        DeviceAddressBookPermissionDTO dto = new DeviceAddressBookPermissionDTO();
        dto.setMacAddress(OTHER_MAC);
        dto.setTargetMac(MAC);
        dto.setHasPermission(true);

        Result<Void> result = controller.updatePermission(dto);

        assertEquals("无权限操作该设备", result.getMsg());
        verify(addressBookService, never()).saveOrUpdate(OTHER_MAC, MAC, null, true);
    }

    private DeviceController controller(DeviceService deviceService, DeviceAddressBookService addressBookService) {
        return new DeviceController(
                deviceService,
                addressBookService,
                mock(RedisUtils.class),
                mock(SysParamsService.class));
    }

    private DeviceEntity ownedDevice() {
        DeviceEntity entity = new DeviceEntity();
        entity.setId(DEVICE_ID);
        entity.setUserId(USER_ID);
        entity.setAutoUpdate(1);
        return entity;
    }

    private UserDetail currentUser() {
        UserDetail user = new UserDetail();
        user.setId(USER_ID);
        return user;
    }
}
