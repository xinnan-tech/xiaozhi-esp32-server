package xiaozhi.modules.device.service;

import xiaozhi.modules.device.entity.DeviceExtEntity;

public interface DeviceExtService {

    /** 取一个设备的扩展字段;无则 null。 */
    DeviceExtEntity getByDeviceId(String deviceId);

    /** 整体覆盖一个设备的扩展字段(JSON 字符串)。 */
    void saveOrUpdate(String deviceId, String extJson);
}
