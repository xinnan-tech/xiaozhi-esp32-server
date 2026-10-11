package xiaozhi.modules.correctword.service;

import java.util.List;
import java.util.Map;

import xiaozhi.common.page.PageData;
import xiaozhi.modules.correctword.dto.CorrectWordFileCreateDTO;
import xiaozhi.modules.correctword.vo.CorrectWordFileVO;
import xiaozhi.modules.correctword.vo.CorrectWordSimpleVO;

public interface CorrectWordFileService {

    /**
     * Create replacement word file
     *
     * @param dto creation parameters
     * @return File VO
     */
    CorrectWordFileVO createFile(CorrectWordFileCreateDTO dto);

    /**
     * Update replacement word file (full replacement)
     *
     * @param fileId File ID
     * @param dto    Modification parameters
     */
    void updateFile(String fileId, CorrectWordFileCreateDTO dto);

    /**
     * Get the list of replacement-word files for the current user
     *
     * @param params Pagination parameters
     * @return Paged data
     */
    PageData<CorrectWordFileVO> listFiles(Map<String, Object> params);

    /**
     * Get current user's replacement word file list (no pagination, for dropdown selection)
     *
     * @return File list
     */
    List<CorrectWordFileVO> listAllFiles();

    /**
     * Get raw file content (for download)
     *
     * @param fileId File ID
     * @return File entity
     */
    CorrectWordFileVO getFileContent(String fileId);

    /**
     * Delete the replacement word file and all its entries and associated records
     *
     * @param fileId File ID
     */
    void deleteFile(String fileId);

    /**
     * Delete replacement word file association records for Agent (do not delete files)
     *
     * @param agentId Agent ID
     */
    void deleteMappingsByAgentId(String agentId);

    /**
     * Get all replacement terms for the Agent (simplified for device use)
     *
     * @param agentId Agent ID
     * @return List of replacement words
     */
    List<CorrectWordSimpleVO> getAllItemsByAgentId(String agentId);

    /**
     * Get list of replacement word file IDs associated with the Agent
     *
     * @param agentId Agent ID
     * @return List of file IDs
     */
    List<String> getAgentCorrectWordFileIds(String agentId);

    /**
     * Save replacement words file associated with Agent (full replacement)
     *
     * @param agentId Agent ID
     * @param fileIds List of file IDs
     */
    void saveAgentCorrectWords(String agentId, List<String> fileIds);

    /**
     * Batch delete replacement word files
     *
     * @param fileIds List of file IDs
     */
    void batchDeleteFiles(List<String> fileIds);
}
