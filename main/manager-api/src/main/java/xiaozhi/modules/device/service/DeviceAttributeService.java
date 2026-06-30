package xiaozhi.modules.device.service;

import java.util.List;
import java.util.Map;

import xiaozhi.common.service.BaseService;
import xiaozhi.modules.device.entity.DeviceAttributeEntity;

public interface DeviceAttributeService extends BaseService<DeviceAttributeEntity> {

    /**
     * 获取设备所有扩展属性
     * 
     * @param deviceId 设备ID
     * @return key-value 属性映射
     */
    Map<String, String> getAttributesByDeviceId(String deviceId);

    /**
     * 获取单个设备属性
     * 
     * @param deviceId 设备ID
     * @param attrKey  属性key
     * @return 属性值
     */
    String getAttributeValue(String deviceId, String attrKey);

    /**
     * 保存或更新设备属性
     * 
     * @param deviceId  设备ID
     * @param attrKey   属性key
     * @param attrValue 属性值
     */
    void saveOrUpdateAttribute(String deviceId, String attrKey, String attrValue);

    /**
     * 批量保存或更新设备属性
     * 
     * @param deviceId   设备ID
     * @param attributes 属性映射
     */
    void saveOrUpdateAttributes(String deviceId, Map<String, String> attributes);

    /**
     * 删除设备属性
     * 
     * @param deviceId 设备ID
     * @param attrKey  属性key
     */
    void deleteAttribute(String deviceId, String attrKey);

    /**
     * 删除设备所有属性
     * 
     * @param deviceId 设备ID
     */
    void deleteByDeviceId(String deviceId);

    /**
     * 批量删除设备属性
     * 
     * @param deviceIds 设备ID列表
     */
    void deleteByDeviceIds(List<String> deviceIds);
}
