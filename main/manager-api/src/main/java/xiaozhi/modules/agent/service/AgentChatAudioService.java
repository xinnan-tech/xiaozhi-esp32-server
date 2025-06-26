package xiaozhi.modules.agent.service;

import com.baomidou.mybatisplus.extension.service.IService;

import xiaozhi.modules.agent.entity.AgentChatAudioEntity;

/**
 * 智能体聊天音频数据表处理service
 *
 * @author Goody
 * @version 1.0, 2025/5/8
 * @since 1.0.0
 */
public interface AgentChatAudioService extends IService<AgentChatAudioEntity> {
    /**
     * 保存音频数据
     *
     * @param audioData 音频数据
     * @return 音频ID
     */
    String saveAudio(byte[] audioData);

    /**
     * 获取音频数据
     *
     * @param audioId 音频ID
     * @return 音频数据
     */
    byte[] getAudio(String audioId);
}
