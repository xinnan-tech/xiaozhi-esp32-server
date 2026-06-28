package xiaozhi.modules.feedback.dao;

import org.apache.ibatis.annotations.Mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;

import xiaozhi.modules.feedback.entity.EmployeeEntity;

@Mapper
public interface EmployeeDao extends BaseMapper<EmployeeEntity> {
}
