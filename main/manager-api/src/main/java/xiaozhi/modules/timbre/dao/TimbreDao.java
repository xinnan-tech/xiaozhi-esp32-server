package xiaozhi.modules.timbre.dao;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;
import xiaozhi.modules.timbre.entity.TimbreEntity;

/**
 * 音色持久层定义
 * @author zjy
 * @since 2025-3-21
 */
@Mapper
public interface TimbreDao extends BaseMapper<TimbreEntity> {
}