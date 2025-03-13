package xiaozhi.modules.device.service.impl;

import xiaozhi.modules.device.service.DeviceService;
import xiaozhi.modules.device.dto.DeviceDTO;
import xiaozhi.common.page.PageData;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Service;
import java.util.Date;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import xiaozhi.modules.device.entity.DeviceEntity;

@Service
public class DeviceServiceImpl implements DeviceService {
    private final DeviceEntity deviceEntity;

    // 添加构造函数来初始化 deviceMapper
    public DeviceServiceImpl(DeviceEntity deviceEntity) {
        this.deviceEntity = deviceEntity;
    }

    @Override
    public DeviceDTO bindDevice(Long userId, String deviceCode) {
        DeviceDTO device = new DeviceDTO();
        device.setUserId(userId);
        device.setDeviceCode(deviceCode);
        device.setCreateDate(new Date());
        deviceEntity.insert(device);
        return device;
    }

    @Override
    public List<DeviceDTO> getUserDevices(Long userId) {
        return deviceEntity.selectByUserId(userId);
    }

    @Override
    public void unbindDevice(Long userId, Long deviceId) {
        deviceEntity.deleteById(deviceId);
    }

    @Override
    public PageData<DeviceDTO> adminDeviceList(Map<String, Object> params) {
        IPage<DeviceDTO> page = deviceEntity.selectPage(
            new Page<>( 
                Long.parseLong(params.get("page").toString()), 
                Long.parseLong(params.get("limit").toString())
            ),
            new QueryWrapper<DeviceDTO>().allEq(params)
        );
        return new PageData<>(page.getRecords(), page.getTotal());
    }
}