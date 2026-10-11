package xiaozhi.modules.device.service;

import java.util.List;
import java.util.Map;

import xiaozhi.modules.device.entity.DeviceAddressBookEntity;

public interface DeviceAddressBookService {

    /**
     * Get device contacts list
     */
    List<DeviceAddressBookEntity> getAddressBookList(String macAddress);

    /**
     * Get contacts for all devices (for global cache)
     */
    Map<String, Map<String, String>> getAllAddressBooks();

    /**
     * Update alias
     */
    void updateAlias(String macAddress, String targetMac, String alias);

    /**
     * Update permissions
     */
    void updatePermission(String macAddress, String targetMac, Boolean hasPermission);

    /**
     * Add or update contact record
     */
    void saveOrUpdate(String macAddress, String targetMac, String alias, Boolean hasPermission);

    /**
     * Refresh contacts cache
     */
    void refreshCache();

    /**
     * Initiate call by nickname
     * @param callerMac Caller MAC address
     * @param nickname Callee nickname
     * @param isAnswer Whether in answer mode (skip permission check)
     */
    Map<String, Object> callByNickname(String callerMac, String nickname, boolean isAnswer);

    /**
     * Batch delete contact records associated with devices
     */
    void deleteByMacAddresses(List<String> macAddresses);
}