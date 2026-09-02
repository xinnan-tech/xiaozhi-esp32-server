package xiaozhi.modules.device.service;

import java.util.Date;
import java.util.List;
import java.util.Map;

import xiaozhi.common.page.PageData;
import xiaozhi.common.service.BaseService;
import xiaozhi.modules.device.dto.DeviceManualAddDTO;
import xiaozhi.modules.device.dto.DevicePageUserDTO;
import xiaozhi.modules.device.dto.DeviceReportReqDTO;
import xiaozhi.modules.device.dto.DeviceReportRespDTO;
import xiaozhi.modules.device.entity.DeviceEntity;
import xiaozhi.modules.device.vo.UserShowDeviceListVO;

public interface DeviceService extends BaseService<DeviceEntity> {
    /**
     * 获取设备在线数据
     */
    String getDeviceOnlineData(String agentId);

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
     * 获取用户指定智能体的设备列表（带时区处理），
     */
    List<UserShowDeviceListVO> getUserDeviceList(Long userId, String agentId);

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

    /**
     * 获取这个智能体设备理的最近的最后连接时间
     * 
     * @param agentId 智能体id
     * @return 返回设备最近的最后连接时间
     */
    Date getLatestLastConnectionTime(String agentId);

    /**
     * 手动添加设备
     */
    void manualAddDevice(Long userId, DeviceManualAddDTO dto);

    /**
     * 更新设备连接信息
     */
    void updateDeviceConnectionInfo(String agentId, String deviceId, String appVersion);

    /**
     * 生成WebSocket认证token
     *
     * @param clientId 客户端ID
     * @param username 用户名(通常为deviceId)
     * @return 认证token字符串
     * @throws Exception 生成token时的异常
     */
    String generateWebSocketToken(String clientId, String username) throws Exception;

    /**
     * 根据MAC地址搜索设备
     *
     * @param macAddress MAC地址关键词
     * @param userId     用户ID
     * @return 设备列表
     */
    List<DeviceEntity> searchDevicesByMacAddress(String macAddress, Long userId);

    /**
     * 获取设备工具列表
     */
    Object getDeviceTools(String deviceId);

    /**
     * 调用设备工具
     */
    Object callDeviceTool(String deviceId, String toolName, Map<String, Object> arguments);

    }