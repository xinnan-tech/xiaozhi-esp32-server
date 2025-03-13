package xiaozhi.modules.device.entity;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import xiaozhi.modules.device.dto.DeviceDTO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param; // 新增 Param 注解导入
import java.util.List;

@Mapper
public interface DeviceEntity extends BaseMapper<DeviceDTO> {
    // 新增 @Param 注解保证参数绑定
    List<DeviceDTO> selectByUserId(@Param("userId") Long userId);
    
    // 与 ServiceImpl 中调用的 selectPage 方法签名保持一致
    IPage<DeviceDTO> selectPage(IPage<DeviceDTO> page, QueryWrapper<DeviceDTO> queryWrapper);
}