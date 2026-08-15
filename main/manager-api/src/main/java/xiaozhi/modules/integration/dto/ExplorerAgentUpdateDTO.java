package xiaozhi.modules.integration.dto;

import lombok.Data;

@Data
public class ExplorerAgentUpdateDTO {
    private String agentName;
    private String systemPrompt;
    private String ttsVoiceId;
    private String ttsLanguage;
}
