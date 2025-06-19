package xiaozhi.modules.device.dao;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import xiaozhi.modules.device.entity.DeviceCommandEntity;

import java.util.List;

@Mapper
public interface DeviceCommandDao extends BaseMapper<DeviceCommandEntity> {
    List<DeviceCommandEntity> selectByDeviceId(@Param("deviceId") String deviceId);

    int updateExecuted(@Param("id") String id, @Param("isExecuted") Integer isExecuted);

    DeviceCommandEntity consumeCommand(@Param("id") String id);
}
