package xiaozhi.modules.correctword.service;

import java.util.List;
import java.util.Map;

import xiaozhi.common.page.PageData;
import xiaozhi.modules.correctword.dto.CorrectWordFileCreateDTO;
import xiaozhi.modules.correctword.vo.CorrectWordFileVO;
import xiaozhi.modules.correctword.vo.CorrectWordSimpleVO;

public interface CorrectWordFileService {

    /**
     * 创建替换词文件
     *
     * @param dto 创建参数
     * @return 文件VO
     */
    CorrectWordFileVO createFile(CorrectWordFileCreateDTO dto);

    /**
     * 修改替换词文件（全量替换词条）
     *
     * @param fileId 文件ID
     * @param dto    修改参数
     */
    void updateFile(String fileId, CorrectWordFileCreateDTO dto);

    /**
     * 获取当前用户的替换词文件列表
     *
     * @param params 分页参数
     * @return 分页数据
     */
    PageData<CorrectWordFileVO> listFiles(Map<String, Object> params);

    /**
     * 获取当前用户的替换词文件列表（不分页，用于下拉选择）
     *
     * @return 文件列表
     */
    List<CorrectWordFileVO> listAllFiles();

    /**
     * 获取文件原始内容（用于下载）
     *
     * @param fileId 文件ID
     * @return 文件实体
     */
    CorrectWordFileVO getFileContent(String fileId);

    /**
     * 删除替换词文件及其所有词条和关联记录
     *
     * @param fileId 文件ID
     */
    void deleteFile(String fileId);

    /**
     * 删除智能体关联的替换词文件关联记录（不删文件本身）
     *
     * @param agentId 智能体ID
     */
    void deleteMappingsByAgentId(String agentId);

    /**
     * 获取智能体的所有替换词条（精简版，供设备端使用）
     *
     * @param agentId 智能体ID
     * @return 替换词列表
     */
    List<CorrectWordSimpleVO> getAllItemsByAgentId(String agentId);

    /**
     * 获取智能体关联的替换词文件ID列表
     *
     * @param agentId 智能体ID
     * @return 文件ID列表
     */
    List<String> getAgentCorrectWordFileIds(String agentId);

    /**
     * 保存智能体关联的替换词文件（全量替换）
     *
     * @param agentId 智能体ID
     * @param fileIds 文件ID列表
     */
    void saveAgentCorrectWords(String agentId, List<String> fileIds);

    /**
     * 批量删除替换词文件
     *
     * @param fileIds 文件ID列表
     */
    void batchDeleteFiles(List<String> fileIds);
}
