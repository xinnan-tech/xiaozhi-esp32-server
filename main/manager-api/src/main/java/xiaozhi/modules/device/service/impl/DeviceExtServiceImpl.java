package xiaozhi.modules.device.service.impl;

import org.springframework.stereotype.Service;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;

import xiaozhi.modules.device.dao.DeviceExtDao;
import xiaozhi.modules.device.entity.DeviceExtEntity;
import xiaozhi.modules.device.service.DeviceExtService;

@Service
public class DeviceExtServiceImpl
        extends ServiceImpl<DeviceExtDao, DeviceExtEntity>
        implements DeviceExtService {

    @Override
    public DeviceExtEntity getByDeviceId(String deviceId) {
        if (deviceId == null || deviceId.isBlank()) {
            return null;
        }
        // deviceId 即主键(@TableId IdType.INPUT),直接 getById
        return this.getById(deviceId);
    }

    @Override
    public void saveOrUpdate(String deviceId, String extJson) {
        DeviceExtEntity e = getByDeviceId(deviceId);
        if (e == null) {
            e = new DeviceExtEntity();
            e.setDeviceId(deviceId);
        }
        e.setExtJson(extJson);
        this.saveOrUpdate(e);
    }
}
