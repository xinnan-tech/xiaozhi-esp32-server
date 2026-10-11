package xiaozhi.modules.agent.dto;

import java.io.Serializable;
import java.math.BigDecimal;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import com.fasterxml.jackson.core.type.TypeReference;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import xiaozhi.common.utils.JsonUtils;

/**
 * Agent update DTO.
 * Used specifically for agent updates. All fields are optional and only
 * provided values will be updated.
 */
@Data
@Schema(description = "Agent update object")
public class AgentUpdateDTO implements Serializable {
    private static final long serialVersionUID = 1L;

    @Schema(description = "Agent code", example = "AGT_1234567890", nullable = true)
    private String agentCode;

    @Schema(description = "Agent name", example = "Support Assistant", nullable = true)
    private String agentName;

    @Schema(description = "ASR model ID", example = "asr_model_02", nullable = true)
    private String asrModelId;

    @Schema(description = "VAD model ID", example = "vad_model_02", nullable = true)
    private String vadModelId;

    @Schema(description = "LLM model ID", example = "llm_model_02", nullable = true)
    private String llmModelId;

    @Schema(description = "Small model ID", example = "slm_model_02", nullable = true)
    private String slmModelId;

    @Schema(description = "VLLM model ID", example = "vllm_model_02", required = false)
    private String vllmModelId;

    @Schema(description = "TTS model ID", example = "tts_model_02", required = false)
    private String ttsModelId;

    @Schema(description = "Voice ID", example = "voice_02", nullable = true)
    private String ttsVoiceId;

    @Schema(description = "Voice language", example = "English", nullable = true)
    private String ttsLanguage;

    @Schema(description = "TTS volume", example = "50", nullable = true)
    private Integer ttsVolume;

    @Schema(description = "TTS speed", example = "50", nullable = true)
    private Integer ttsRate;

    @Schema(description = "TTS pitch", example = "50", nullable = true)
    private Integer ttsPitch;

    @Schema(description = "Memory model ID", example = "mem_model_02", nullable = true)
    private String memModelId;

    @Schema(description = "Intent model ID", example = "intent_model_02", nullable = true)
    private String intentModelId;

    @Schema(description = "Plugin function information", nullable = true)
    private List<FunctionInfo> functions;

    @Schema(description = "System prompt", example = "You are a professional support assistant who helps answer user questions.", nullable = true)
    private String systemPrompt;

    @Schema(description = "Summary memory", example = "Build a growing memory graph that preserves key information while tracking how it evolves over time.\n"
            + "Summarize the user's important details from the conversation so future interactions can be more personalized.", nullable = true)
    private String summaryMemory;

    @Schema(description = "Chat-history mode (0 disabled, 1 text only, 2 text and audio)", example = "2", nullable = true)
    private Integer chatHistoryConf;

    @Schema(description = "Language code", example = "en_US", nullable = true)
    private String langCode;

    @Schema(description = "Interaction language", example = "English", nullable = true)
    private String language;

    @Schema(description = "Sort order", example = "1", nullable = true)
    private Integer sort;

    @Schema(description = "Context-provider configuration", nullable = true)
    private List<ContextProviderDTO> contextProviders;

    @Schema(description = "替换词文件ID列表", nullable = true)
    private List<String> correctWordFileIds;

    @Schema(description = "标签名称列表", nullable = true)
    private List<String> tagNames;

    @Schema(description = "标签ID列表", nullable = true)
    private List<String> tagIds;

    @Data
    @Schema(description = "Plugin function information")
    public static class FunctionInfo implements Serializable {
        private static final TypeReference<HashMap<String, Object>> PARAM_INFO_TYPE = new TypeReference<>() {};

        @Schema(description = "Plugin ID", example = "plugin_01")
        private String pluginId;

        @Schema(description = "Function parameter information", nullable = true)
        private HashMap<String, Object> paramInfo = new HashMap<>();

        public void setParamInfo(Object paramInfo) {
            this.paramInfo = normalizeParamInfo(paramInfo);
        }

        private static HashMap<String, Object> normalizeParamInfo(Object paramInfo) {
            if (paramInfo == null || (paramInfo instanceof String value && value.trim().isEmpty())) {
                return new HashMap<>();
            }
            if (paramInfo instanceof String value) {
                return JsonUtils.parseObject(value, PARAM_INFO_TYPE);
            }
            if (paramInfo instanceof Map<?, ?> value) {
                HashMap<String, Object> normalized = new HashMap<>();
                value.forEach((key, entryValue) -> {
                    if (key != null) normalized.put(String.valueOf(key), entryValue);
                });
                return normalized;
            }
            return JsonUtils.parseObject(JsonUtils.toJsonString(paramInfo), PARAM_INFO_TYPE);
        }

        private static final long serialVersionUID = 1L;
    }
}
