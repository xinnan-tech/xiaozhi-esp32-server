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
import xiaozhi.modules.device.mapper.DeviceMapper;

@Service
public class DeviceServiceImpl implements DeviceService {
    private final DeviceMapper deviceMapper;

    // 添加构造函数来初始化 deviceMapper
    public DeviceServiceImpl(DeviceMapper deviceMapper) {
        this.deviceMapper = deviceMapper;
    }

    @Override
    public DeviceDTO bindDevice(Long userId, String deviceCode) {
        DeviceDTO device = new DeviceDTO();
        device.setUserId(userId);
        device.setDeviceCode(deviceCode);
        device.setCreateDate(new Date());
        deviceMapper.insert(device);
        return device;
    }

    @Override
    public List<DeviceDTO> getUserDevices(Long userId) {
        return deviceMapper.selectByUserId(userId);
    }

    @Override
    public void unbindDevice(Long userId, Long deviceId) {
        deviceMapper.deleteById(deviceId);
    }

    @Override
    public PageData<DeviceDTO> adminDeviceList(Map<String, Object> params) {
        IPage<DeviceDTO> page = deviceMapper.selectPage(
            new Page<>( 
                Long.parseLong(params.get("page").toString()), 
                Long.parseLong(params.get("limit").toString())
            ),
            new QueryWrapper<DeviceDTO>().allEq(params)
        );
        return new PageData<>(page.getRecords(), page.getTotal());
    }
}