package xiaozhi.modules.device.service.impl;

import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

import xiaozhi.common.exception.RenException;
import xiaozhi.common.redis.RedisUtils;
import xiaozhi.common.utils.TestMessageSupport;
import xiaozhi.modules.device.dao.DeviceDao;
import xiaozhi.modules.device.entity.DeviceEntity;
import xiaozhi.modules.device.service.DeviceAddressBookService;

class DeviceServiceImplOwnershipTest {
    @BeforeEach
    void installMessages() {
        TestMessageSupport.install();
    }

    @Test
    void unbindRejectsAnotherOwnersDeviceBeforeAnySideEffect() {
        DeviceDao deviceDao = mock(DeviceDao.class);
        DeviceAddressBookService addressBooks = mock(DeviceAddressBookService.class);
        DeviceEntity anotherOwnersDevice = new DeviceEntity();
        anotherOwnersDevice.setId("device-1");
        anotherOwnersDevice.setUserId(99L);
        anotherOwnersDevice.setMacAddress("AA:BB:CC:DD:EE:FF");
        when(deviceDao.selectById("device-1")).thenReturn(anotherOwnersDevice);

        DeviceServiceImpl service = new DeviceServiceImpl(
                deviceDao, null, null, mock(RedisUtils.class), null, addressBooks);
        ReflectionTestUtils.setField(service, "baseDao", deviceDao);

        assertThrows(RenException.class, () -> service.unbindDevice(41L, "device-1"));
        verify(deviceDao, never()).delete(org.mockito.ArgumentMatchers.any());
        verify(addressBooks, never()).deleteByMacAddresses(org.mockito.ArgumentMatchers.any());
    }
}
