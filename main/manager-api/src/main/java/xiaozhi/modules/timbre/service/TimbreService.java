package xiaozhi.modules.timbre.service;

import java.util.List;

import xiaozhi.common.page.PageData;
import xiaozhi.common.service.BaseService;
import xiaozhi.modules.timbre.dto.TimbreDataDTO;
import xiaozhi.modules.timbre.dto.TimbrePageDTO;
import xiaozhi.modules.timbre.entity.TimbreEntity;
import xiaozhi.modules.timbre.vo.TimbreDetailsVO;

/**
 * 音色的业务层的定义
 * 
 * @author zjy
 * @since 2025-3-21
 */
public interface TimbreService extends BaseService<TimbreEntity> {
    /**
     * 分页获取音色指定tts的下的音色
     * 
     * @param dto 分页查找参数
     * @return 音色列表分页数据
     */
    PageData<TimbreDetailsVO> page(TimbrePageDTO dto);

    /**
     * 获取音色指定id的详情信息
     * 
     * @param timbreId 音色表id
     * @return 音色信息
     */
    TimbreDetailsVO get(Long timbreId);

    /**
     * 保存音色信息
     * 
     * @param dto 需要保存数据
     */
    void save(TimbreDataDTO dto);

    /**
     * 保存音色信息
     * 
     * @param timbreId 需要修改的id
     * @param dto      需要修改的数据
     */
    void update(String timbreId, TimbreDataDTO dto);

    /**
     * 批量删除音色
     * 
     * @param ids 需要被删除的音色id列表
     */
    void delete(String[] ids);

    List<String> getVoiceNames(String ttsModelId, String voiceName);
}