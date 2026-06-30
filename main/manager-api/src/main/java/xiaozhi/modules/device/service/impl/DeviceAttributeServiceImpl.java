package xiaozhi.modules.device.service.impl;

import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.UpdateWrapper;

import lombok.AllArgsConstructor;
import xiaozhi.common.service.impl.BaseServiceImpl;
import xiaozhi.modules.device.dao.DeviceAttributeDao;
import xiaozhi.modules.device.entity.DeviceAttributeEntity;
import xiaozhi.modules.device.service.DeviceAttributeService;

@Service
@AllArgsConstructor
public class DeviceAttributeServiceImpl extends BaseServiceImpl<DeviceAttributeDao, DeviceAttributeEntity>
        implements DeviceAttributeService {

    private final DeviceAttributeDao deviceAttributeDao;

    @Override
    public Map<String, String> getAttributesByDeviceId(String deviceId) {
        if (StringUtils.isBlank(deviceId)) {
            return Collections.emptyMap();
        }
        QueryWrapper<DeviceAttributeEntity> wrapper = new QueryWrapper<>();
        wrapper.eq("device_id", deviceId);
        List<DeviceAttributeEntity> list = deviceAttributeDao.selectList(wrapper);
        return list.stream()
                .collect(Collectors.toMap(DeviceAttributeEntity::getAttrKey, DeviceAttributeEntity::getAttrValue,
                        (v1, v2) -> v1));
    }

    @Override
    public String getAttributeValue(String deviceId, String attrKey) {
        if (StringUtils.isBlank(deviceId) || StringUtils.isBlank(attrKey)) {
            return null;
        }
        QueryWrapper<DeviceAttributeEntity> wrapper = new QueryWrapper<>();
        wrapper.eq("device_id", deviceId).eq("attr_key", attrKey);
        DeviceAttributeEntity entity = deviceAttributeDao.selectOne(wrapper);
        return entity == null ? null : entity.getAttrValue();
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void saveOrUpdateAttribute(String deviceId, String attrKey, String attrValue) {
        if (StringUtils.isBlank(deviceId) || StringUtils.isBlank(attrKey)) {
            return;
        }
        QueryWrapper<DeviceAttributeEntity> wrapper = new QueryWrapper<>();
        wrapper.eq("device_id", deviceId).eq("attr_key", attrKey);
        DeviceAttributeEntity entity = deviceAttributeDao.selectOne(wrapper);
        if (entity == null) {
            entity = new DeviceAttributeEntity();
            entity.setDeviceId(deviceId);
            entity.setAttrKey(attrKey);
            entity.setAttrValue(attrValue);
            deviceAttributeDao.insert(entity);
        } else {
            entity.setAttrValue(attrValue);
            deviceAttributeDao.updateById(entity);
        }
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void saveOrUpdateAttributes(String deviceId, Map<String, String> attributes) {
        if (StringUtils.isBlank(deviceId) || attributes == null || attributes.isEmpty()) {
            return;
        }
        attributes.forEach((key, value) -> saveOrUpdateAttribute(deviceId, key, value));
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deleteAttribute(String deviceId, String attrKey) {
        if (StringUtils.isBlank(deviceId) || StringUtils.isBlank(attrKey)) {
            return;
        }
        UpdateWrapper<DeviceAttributeEntity> wrapper = new UpdateWrapper<>();
        wrapper.eq("device_id", deviceId).eq("attr_key", attrKey);
        deviceAttributeDao.delete(wrapper);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deleteByDeviceId(String deviceId) {
        if (StringUtils.isBlank(deviceId)) {
            return;
        }
        UpdateWrapper<DeviceAttributeEntity> wrapper = new UpdateWrapper<>();
        wrapper.eq("device_id", deviceId);
        deviceAttributeDao.delete(wrapper);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deleteByDeviceIds(List<String> deviceIds) {
        if (deviceIds == null || deviceIds.isEmpty()) {
            return;
        }
        UpdateWrapper<DeviceAttributeEntity> wrapper = new UpdateWrapper<>();
        wrapper.in("device_id", deviceIds);
        deviceAttributeDao.delete(wrapper);
    }
}
