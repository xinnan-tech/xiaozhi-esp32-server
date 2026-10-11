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
     * Get device online data
     */
    String getDeviceOnlineData(String agentId);

    /**
     * Check if device is active
     */
    DeviceReportRespDTO checkDeviceActive(String macAddress, String clientId,
            DeviceReportReqDTO deviceReport);

    /**
     * Retrieve device list for user-specified Agent,
     */
    List<DeviceEntity> getUserDevices(Long userId, String agentId);

    /**
     * Get device list for user-specified agent (with timezone handling),
     */
    List<UserShowDeviceListVO> getUserDeviceList(Long userId, String agentId);

    /**
     * Unbind device
     */
    void unbindDevice(Long userId, String deviceId);

    /**
     * Device Activation
     */
    Boolean deviceActivation(String agentId, String activationCode);

    /**
     * Delete all devices for this user
     * 
     * @param userId User ID
     */
    void deleteByUserId(Long userId);

    /**
     * Delete all devices associated with the specified Agent
     * 
     * @param agentId Agent ID
     */
    void deleteByAgentId(String agentId);

    /**
     * Get device count for specified user
     * 
     * @param userId User ID
     * @return Device count
     */
    Long selectCountByUserId(Long userId);

    /**
     * Paginate to retrieve all device information
     *
     * @param dto Pagination search parameters
     * @return Paginated user list data
     */
    PageData<UserShowDeviceListVO> page(DevicePageUserDTO dto);

    /**
     * Get device info by MAC address
     * 
     * @param macAddress MAC address
     * @return Device info
     */
    DeviceEntity getDeviceByMacAddress(String macAddress);

    /**
     * Get activation code by device ID
     * 
     * @param deviceId Device ID
     * @return activation code
     */
    String geCodeByDeviceId(String deviceId);

    /**
     * Get the last connection time for this agent device
     * 
     * @param agentId Agent ID
     * @return Returns the device's most recent last connection time
     */
    Date getLatestLastConnectionTime(String agentId);

    /**
     * Add device manually
     */
    void manualAddDevice(Long userId, DeviceManualAddDTO dto);

    /**
     * Update device connection info
     */
    void updateDeviceConnectionInfo(String agentId, String deviceId, String appVersion);

    /**
     * Generate WebSocket authentication token
     *
     * @param clientId Client ID
     * @param username Username (typically deviceId)
     * @return Authentication token string
     * @throws Exception Exception during token generation
     */
    String generateWebSocketToken(String clientId, String username) throws Exception;

    /**
     * Search device by MAC address
     *
     * @param macAddress MAC address keyword
     * @param userId User ID
     * @return Device list
     */
    List<DeviceEntity> searchDevicesByMacAddress(String macAddress, Long userId);

    /**
     * Get device tool list
     */
    Object getDeviceTools(String deviceId);

    /**
     * Invoke Device Tool
     */
    Object callDeviceTool(String deviceId, String toolName, Map<String, Object> arguments);

    }