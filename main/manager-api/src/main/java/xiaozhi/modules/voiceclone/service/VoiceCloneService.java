package xiaozhi.modules.voiceclone.service;

import java.util.List;
import java.util.Map;

import org.springframework.web.multipart.MultipartFile;

import xiaozhi.common.page.PageData;
import xiaozhi.common.service.BaseService;
import xiaozhi.modules.voiceclone.dto.VoiceCloneDTO;
import xiaozhi.modules.voiceclone.dto.VoiceCloneResponseDTO;
import xiaozhi.modules.voiceclone.entity.VoiceCloneEntity;

/**
 * 声音克隆管理
 */
public interface VoiceCloneService extends BaseService<VoiceCloneEntity> {

    /**
     * 分页查询
     */
    PageData<VoiceCloneEntity> page(Map<String, Object> params);

    /**
     * 保存声音克隆
     */
    void save(VoiceCloneDTO dto);

    /**
     * 批量删除
     */
    void delete(String[] ids);

    /**
     * 根据用户ID查询声音克隆列表
     * 
     * @param userId 用户ID
     * @return 声音克隆列表
     */
    List<VoiceCloneEntity> getByUserId(Long userId);

    /**
     * 分页查询带模型名称和用户名称的声音克隆列表
     */
    PageData<VoiceCloneResponseDTO> pageWithNames(Map<String, Object> params);

    /**
     * 根据ID查询带模型名称和用户名称的声音克隆信息
     */
    VoiceCloneResponseDTO getByIdWithNames(String id);

    /**
     * 根据用户ID查询带模型名称的声音克隆列表
     */
    List<VoiceCloneResponseDTO> getByUserIdWithNames(Long userId);

    /**
     * 上传音频文件
     */
    void uploadVoice(String id, MultipartFile voiceFile) throws Exception;

    /**
     * 更新声音克隆名称
     */
    void updateName(String id, String name);

    /**
     * 获取音频数据
     */
    byte[] getVoiceData(String id);

    /**
     * 克隆音频，调用火山引擎进行语音复刻训练
     * 
     * @param cloneId 语音克隆记录ID
     */
    void cloneAudio(String cloneId);
}
