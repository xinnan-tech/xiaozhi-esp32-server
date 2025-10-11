package xiaozhi.modules.voiceclone.dao;

import org.apache.ibatis.annotations.Mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;

import xiaozhi.modules.voiceclone.entity.VoiceCloneEntity;

/**
 * 声音克隆
 */
@Mapper
public interface VoiceCloneDao extends BaseMapper<VoiceCloneEntity> {

}
