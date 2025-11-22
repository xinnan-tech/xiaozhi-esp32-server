package xiaozhi.modules.voiceclone.dao;

import java.util.List;

import org.apache.ibatis.annotations.Mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;

import xiaozhi.modules.model.dto.VoiceDTO;
import xiaozhi.modules.voiceclone.entity.VoiceCloneEntity;

/**
 * 声音克隆
 */
@Mapper
public interface VoiceCloneDao extends BaseMapper<VoiceCloneEntity> {
    /**
     * 获取用户训练成功的音色列表
     * 
     * @param modelId 模型ID
     * @param userId  用户ID
     * @return 训练成功的音色列表
     */
    List<VoiceDTO> getTrainSuccess(String modelId, Long userId);

}
