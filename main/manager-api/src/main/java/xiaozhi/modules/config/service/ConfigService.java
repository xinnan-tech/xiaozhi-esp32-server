package xiaozhi.modules.config.service;

import java.util.List;
import java.util.Map;

public interface ConfigService {
    /**
     * Get server config
     *
     * @param isCache Whether to cache
     * @return Config info
     */
    Map<String, Object> getConfig(Boolean isCache);

    /**
     * Get agent model config
     *
     * @param macAddress     MAC address
     * @param selectedModule Model instance initialized by the client
     * @return Model configuration info
     */
    Map<String, Object> getAgentModels(String macAddress, Map<String, String> selectedModule);

    /**
     * Get agent replacement words
     *
     * @param macAddress Device MAC address
     * @return List of replacement words, format: ["template1|template01", "template2|template02"]
     */
    List<String> getCorrectWords(String macAddress);
}
