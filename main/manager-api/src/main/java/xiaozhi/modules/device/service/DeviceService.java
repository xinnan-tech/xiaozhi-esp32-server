package xiaozhi.modules.device.service;

import xiaozhi.common.page.PageData;
import xiaozhi.modules.device.dto.DeviceDTO;

import java.util.List;
import java.util.Map;

public interface DeviceService {
    DeviceDTO bindDevice(Long userId, String deviceCode);
    
    List<DeviceDTO> getUserDevices(Long userId);
    
    void unbindDevice(Long userId, Long deviceId);
    
    PageData<DeviceDTO> adminDeviceList(Map<String, Object> params);
}