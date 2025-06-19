package xiaozhi.modules.device.service.impl;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import xiaozhi.modules.device.dao.DeviceCommandDao;
import xiaozhi.modules.device.entity.DeviceCommandEntity;
import xiaozhi.modules.device.service.DeviceCommandService;

import java.util.Date;
import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class DeviceCommandServiceImpl implements DeviceCommandService {
    private final DeviceCommandDao deviceCommandDao;

    @Override
    public void addCommand(DeviceCommandEntity entity) {
        entity.setId(UUID.randomUUID().toString().replace("-", ""));
        entity.setIsExecuted(0);
        entity.setCreateDate(new Date());
        deviceCommandDao.insert(entity);
    }

    @Override
    public List<DeviceCommandEntity> getCommandsByDeviceId(String deviceId) {
        return deviceCommandDao.selectByDeviceId(deviceId);
    }

    @Override
    public void setCommandExecuted(String id) {
        deviceCommandDao.updateExecuted(id, 1);
    }

    @Override
    public DeviceCommandEntity getById(String id) {
        return deviceCommandDao.selectById(id);
    }

    @Override
    public DeviceCommandEntity consumeCommand(String deviceId) {
        // 查询未执行的第一条命令
        DeviceCommandEntity entity = deviceCommandDao.consumeCommand(deviceId);
        if (entity != null) {
            // 更新为已执行
            deviceCommandDao.updateExecuted(entity.getId(), 1);
        }
        return entity;
    }
}
