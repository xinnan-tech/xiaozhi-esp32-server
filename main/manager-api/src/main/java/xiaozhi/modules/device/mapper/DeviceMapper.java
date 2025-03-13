package xiaozhi.modules.device.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
// 正确的导入路径应该是 com.baomidou.mybatisplus.core.conditions.query.QueryWrapper
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import xiaozhi.modules.device.dto.DeviceDTO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param; // 新增 Param 注解导入
import java.util.List;

@Mapper
public interface DeviceMapper extends BaseMapper<DeviceDTO> {
    // 新增 @Param 注解保证参数绑定
    List<DeviceDTO> selectByUserId(@Param("userId") Long userId);
    
    // 与 ServiceImpl 中调用的 selectPage 方法签名保持一致
    IPage<DeviceDTO> selectPage(IPage<DeviceDTO> page, QueryWrapper<DeviceDTO> queryWrapper);
}