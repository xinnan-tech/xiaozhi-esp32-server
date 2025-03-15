package xiaozhi.modules.device.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import org.springframework.stereotype.Service;
import xiaozhi.common.page.PageData;
import xiaozhi.common.service.impl.BaseServiceImpl;
import xiaozhi.modules.device.dao.DeviceDao;
import xiaozhi.modules.device.dto.DeviceHeaderDTO;
import xiaozhi.modules.device.entity.DeviceEntity;
import xiaozhi.modules.device.service.DeviceService;

import java.util.Date;
import java.util.List;
import java.util.Map;

@Service
public class DeviceServiceImpl extends BaseServiceImpl<DeviceDao, DeviceEntity> implements DeviceService {
    private final DeviceDao deviceDao;

    // 添加构造函数来初始化 deviceMapper
    public DeviceServiceImpl(DeviceDao deviceDao) {
        this.deviceDao = deviceDao;
    }

    @Override
    public DeviceEntity bindDevice(Long userId, DeviceHeaderDTO deviceHeader) {
        DeviceEntity device = new DeviceEntity();
        device.setUserId(userId);
        device.setMacAddress(deviceHeader.getDeviceId());
        device.setCreateDate(new Date());
        deviceDao.insert(device);
        return device;
    }

    @Override
    public List<DeviceEntity> getUserDevices(Long userId) {
        QueryWrapper<DeviceEntity> wrapper = new QueryWrapper<>();
        wrapper.eq("user_id", userId);
        return deviceDao.selectList(wrapper);
    }

    @Override
    public void unbindDevice(Long userId, Long deviceId) {
        deviceDao.deleteById(deviceId);
    }

    @Override
    public PageData<DeviceEntity> adminDeviceList(Map<String, Object> params) {
        IPage<DeviceEntity> page = deviceDao.selectPage(
                getPage(params, "sort", true),
                new QueryWrapper<>()
        );
        return new PageData<>(page.getRecords(), page.getTotal());
    }

}