package xiaozhi.modules.timbre.service;

import java.util.List;

import xiaozhi.common.page.PageData;
import xiaozhi.common.service.BaseService;
import xiaozhi.modules.model.dto.VoiceDTO;
import xiaozhi.modules.timbre.dto.TimbreDataDTO;
import xiaozhi.modules.timbre.dto.TimbrePageDTO;
import xiaozhi.modules.timbre.entity.TimbreEntity;
import xiaozhi.modules.timbre.vo.TimbreDetailsVO;

/**
 * Timbre business layer definition
 * 
 * @author zjy
 * @since 2025-3-21
 */
public interface TimbreService extends BaseService<TimbreEntity> {
    /**
     * Get paginated timbres under specified TTS
     * 
     * @param dto Pagination search parameters
     * @return Paginated timbre list data
     */
    PageData<TimbreDetailsVO> page(TimbrePageDTO dto);

    /**
     * Get timbre details by specified ID
     * 
     * @param timbreId Timbre table ID
     * @return Timbre information
     */
    TimbreDetailsVO get(String timbreId);

    /**
     * Save timbre information
     * 
     * @param dto Data to be saved
     */
    void save(TimbreDataDTO dto);

    /**
     * Save timbre information
     * 
     * @param timbreId ID that needs to be modified
     * @param dto      Data that needs to be modified
     */
    void update(String timbreId, TimbreDataDTO dto);

    /**
     * Batch delete timbres
     * 
     * @param ids List of timbre IDs to be deleted
     */
    void delete(String[] ids);

    List<VoiceDTO> getVoiceNames(String ttsModelId, String voiceName);

    String getDefaultLanguageById(String id);

    /**
     * Get timbre name by ID
     * 
     * @param id Timbre ID
     * @return Timbre name
     */
    String getTimbreNameById(String id);

    /**
     * Get voice information by voice code.
     *
     * @param ttsModelId voice model ID
     * @param voiceCode  voice code
     * @return voice information
     */
    VoiceDTO getByVoiceCode(String ttsModelId, String voiceCode);
}
