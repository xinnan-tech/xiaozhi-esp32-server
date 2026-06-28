package xiaozhi.modules.feedback.dao;

import org.apache.ibatis.annotations.Mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;

import xiaozhi.modules.feedback.entity.FeedbackRecordEntity;

@Mapper
public interface FeedbackRecordDao extends BaseMapper<FeedbackRecordEntity> {
}
