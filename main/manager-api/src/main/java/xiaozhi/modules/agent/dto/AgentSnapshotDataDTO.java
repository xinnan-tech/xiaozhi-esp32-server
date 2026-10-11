package xiaozhi.modules.agent.dto;

import java.io.Serializable;
import java.util.List;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
@Schema(description = "智能体快照数据")
public class AgentSnapshotDataDTO implements Serializable {
    private static final long serialVersionUID = 1L;

    private String agentCode;
    private String agentName;
    private String asrModelId;
    private String vadModelId;
    private String llmModelId;
    private String slmModelId;
    private String vllmModelId;
    private String ttsModelId;
    private String ttsVoiceId;
    private String ttsLanguage;
    private Integer ttsVolume;
    private Integer ttsRate;
    private Integer ttsPitch;
    private String memModelId;
    private String intentModelId;
    private Integer chatHistoryConf;
    private String systemPrompt;
    private String summaryMemory;
    private String langCode;
    private String language;
    private Integer sort;
    private List<AgentUpdateDTO.FunctionInfo> functions;
    private List<ContextProviderDTO> contextProviders;
    private List<String> correctWordFileIds;
    private List<String> tagNames;
    private List<AgentSnapshotTagDTO> tags;
}
