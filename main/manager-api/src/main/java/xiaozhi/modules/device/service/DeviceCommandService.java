package xiaozhi.modules.device.service;

import xiaozhi.modules.device.entity.DeviceCommandEntity;

import java.util.List;

public interface DeviceCommandService {
    void addCommand(DeviceCommandEntity entity);

    List<DeviceCommandEntity> getCommandsByDeviceId(String deviceId);

    void setCommandExecuted(String id);

    DeviceCommandEntity getById(String id);

    DeviceCommandEntity consumeCommand(String deviceId);
}
