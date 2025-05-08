package xiaozhi.modules.device.dao;

import org.apache.ibatis.annotations.Mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;

import xiaozhi.modules.device.entity.DeviceEntity;

import java.util.Date;
import java.util.List;

@Mapper
public interface DeviceDao extends BaseMapper<DeviceEntity> {
    /**
     * 获取此智能体全部设备的最后连接时间
     * @param agentId 智能体id
     * @return
     */
    Date getAllLastConnectedAtByAgentId(String agentId);

}