package xiaozhi.modules.agent.service;

import com.baomidou.mybatisplus.extension.repository.IRepository;

import xiaozhi.modules.agent.entity.AgentChatAudioEntity;

/**
 * Agent chat audio data table processing service
 *
 * @author Goody
 * @version 1.0, 2025/5/8
 * @since 1.0.0
 */
public interface AgentChatAudioService extends IRepository<AgentChatAudioEntity> {
    /**
     * Save audio data
     *
     * @param audioData Audio data
     * @return Audio ID
     */
    String saveAudio(byte[] audioData);

    /**
     * Get audio data
     *
     * @param audioId Audio ID
     * @return Audio data
     */
    byte[] getAudio(String audioId);
}
