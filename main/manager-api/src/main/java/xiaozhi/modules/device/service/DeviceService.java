package xiaozhi.modules.device.service;

import java.util.List;

import xiaozhi.modules.device.dto.DeviceBindDTO;
import xiaozhi.modules.device.dto.DeviceReportReqDTO;
import xiaozhi.modules.device.dto.DeviceReportRespDTO;
import xiaozhi.modules.device.entity.DeviceEntity;

public interface DeviceService {

    /**
     * 根据Mac地址获取设备信息
     */
    DeviceEntity getDeviceById(String macAddress);

    /**
     * 检查设备是否激活
     */
    DeviceReportRespDTO checkDeviceActive(String macAddress, String deviceId, String clientId,
            DeviceReportReqDTO deviceReport);

    /**
     * 绑定设备
     */
    DeviceEntity bindDevice(DeviceBindDTO deviceHeader);

    /**
     * 获取用户设备列表
     */
    List<DeviceEntity> getUserDevices(Long userId, String agentId);

    /**
     * 解绑设备
     */
    void unbindDevice(Long userId, String deviceId);

    /**
     * 设备激活
     */
    Boolean deviceActivation(String activationCode);
}