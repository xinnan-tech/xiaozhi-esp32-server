package xiaozhi.modules.agent.service;

import java.util.List;

import xiaozhi.modules.agent.dto.AgentVoicePrintSaveDTO;
import xiaozhi.modules.agent.dto.AgentVoicePrintUpdateDTO;
import xiaozhi.modules.agent.vo.AgentVoicePrintVO;

/**
 * 智能体声纹处理service
 *
 * @author zjy
 */
public interface AgentVoicePrintService {
    /**
     * 添加智能体新的声纹
     *
     * @param dto 保存智能体声纹的数据
     * @return T:成功 F：失败
     */
    boolean insert(AgentVoicePrintSaveDTO dto);

    /**
     * 删除智能体的指的声纹
     *
     * @param userId       当前登录的用户id
     * @param voicePrintId 声纹id
     * @return 是否成功 T:成功 F：失败
     */
    boolean delete(Long userId, String voicePrintId);

    /**
     * 获取指定智能体的所有声纹数据
     *
     * @param userId  当前登录的用户id
     * @param agentId 智能体id
     * @return 声纹数据集合
     */
    List<AgentVoicePrintVO> list(Long userId, String agentId);

    /**
     * 更新智能体的指的声纹数据
     *
     * @param userId 当前登录的用户id
     * @param dto    修改的声纹的数据
     * @return 是否成功 T:成功 F：失败
     */
    boolean update(Long userId, AgentVoicePrintUpdateDTO dto);

}
