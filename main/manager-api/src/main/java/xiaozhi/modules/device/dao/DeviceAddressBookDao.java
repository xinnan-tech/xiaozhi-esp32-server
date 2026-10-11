package xiaozhi.modules.device.dao;

import java.util.List;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;

import xiaozhi.modules.device.entity.DeviceAddressBookEntity;

@Mapper
public interface DeviceAddressBookDao extends BaseMapper<DeviceAddressBookEntity> {

    /**
     * Add device contact record
     */
    int insertAddressBook(DeviceAddressBookEntity entity);

    /**
     * Get device contacts list
     */
    List<DeviceAddressBookEntity> getAddressBookList(@Param("macAddress") String macAddress);

    /**
     * Update alias
     */
    void updateAlias(@Param("macAddress") String macAddress, @Param("targetMac") String targetMac, @Param("alias") String alias);

    /**
     * Update permissions
     */
    void updatePermission(@Param("macAddress") String macAddress, @Param("targetMac") String targetMac, @Param("hasPermission") Boolean hasPermission);

    /**
     * Batch delete contact records associated with devices
     */
    void deleteByMacAddresses(@Param("macAddresses") List<String> macAddresses);
}
