package xiaozhi.modules.device.service;

import java.util.List;
import java.util.Map;

import xiaozhi.modules.device.entity.DeviceAddressBookEntity;

public interface DeviceAddressBookService {

    /**
     * 获取设备通讯录列表
     */
    List<DeviceAddressBookEntity> getAddressBookList(String macAddress);

    /**
     * 获取所有设备的通讯录（全局缓存用）
     */
    Map<String, Map<String, String>> getAllAddressBooks();

    /**
     * 更新别名
     */
    void updateAlias(String macAddress, String targetMac, String alias);

    /**
     * 更新权限
     */
    void updatePermission(String macAddress, String targetMac, Boolean hasPermission);

    /**
     * 添加或更新通讯录记录
     */
    void saveOrUpdate(String macAddress, String targetMac, String alias, Boolean hasPermission);

    /**
     * 刷新通讯录缓存
     */
    void refreshCache();

    /**
     * 根据昵称发起呼叫
     * @param callerMac 主叫方MAC地址
     * @param nickname 被叫方昵称
     * @param isAnswer 是否为接听模式（跳过权限检查）
     */
    Map<String, Object> callByNickname(String callerMac, String nickname, boolean isAnswer);

    /**
     * 批量删除设备相关的通讯录记录
     */
    void deleteByMacAddresses(List<String> macAddresses);
}