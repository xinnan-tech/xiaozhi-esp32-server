package xiaozhi.modules.device.service;

import java.util.List;

import xiaozhi.common.page.PageData;
import xiaozhi.common.service.BaseService;
import xiaozhi.modules.device.dto.DevicePageUserDTO;
import xiaozhi.modules.device.dto.DeviceReportReqDTO;
import xiaozhi.modules.device.dto.DeviceReportRespDTO;
import xiaozhi.modules.device.entity.DeviceEntity;
import xiaozhi.modules.device.vo.UserShowDeviceListVO;

public interface DeviceService extends BaseService<DeviceEntity> {

    /**
     * 检查设备是否激活
     */
    DeviceReportRespDTO checkDeviceActive(String macAddress, String clientId,
            DeviceReportReqDTO deviceReport);

    /**
     * 获取用户指定智能体的设备列表，
     */
    List<DeviceEntity> getUserDevices(Long userId, String agentId);

    /**
     * 解绑设备
     */
    void unbindDevice(Long userId, String deviceId);

    /**
     * 设备激活
     */
    Boolean deviceActivation(String agentId, String activationCode);

    /**
     * 删除此用户的所有设备
     * 
     * @param userId 用户id
     */
    void deleteByUserId(Long userId);

    /**
     * 删除指定智能体关联的所有设备
     * 
     * @param agentId 智能体id
     */
    void deleteByAgentId(String agentId);

    /**
     * 获取指定用户的设备数量
     * 
     * @param userId 用户id
     * @return 设备数量
     */
    Long selectCountByUserId(Long userId);

    /**
     * 分页获取全部设备信息
     *
     * @param dto 分页查找参数
     * @return 用户列表分页数据
     */
    PageData<UserShowDeviceListVO> page(DevicePageUserDTO dto);

    /**
     * 根据MAC地址获取设备信息
     * 
     * @param macAddress MAC地址
     * @return 设备信息
     */
    DeviceEntity getDeviceByMacAddress(String macAddress);

    /**
     * 根据设备ID获取激活码
     * 
     * @param deviceId 设备ID
     * @return 激活码
     */
    String geCodeByDeviceId(String deviceId);
}