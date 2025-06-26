package xiaozhi.modules.agent.dto;

import java.io.Serializable;
import java.util.HashMap;
import java.util.List;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

/**
 * 智能体更新DTO
 * 专用于更新智能体，id字段是必需的，用于标识要更新的智能体
 * 其他字段均为非必填，只更新提供的字段
 */
@Data
@Schema(description = "智能体更新对象")
public class AgentUpdateDTO implements Serializable {
    private static final long serialVersionUID = 1L;

    @Schema(description = "智能体编码", example = "AGT_1234567890", nullable = true)
    private String agentCode;

    @Schema(description = "智能体名称", example = "客服助手", nullable = true)
    private String agentName;

    @Schema(description = "语音识别模型标识", example = "asr_model_02", nullable = true)
    private String asrModelId;

    @Schema(description = "语音活动检测标识", example = "vad_model_02", nullable = true)
    private String vadModelId;

    @Schema(description = "大语言模型标识", example = "llm_model_02", nullable = true)
    private String llmModelId;

    @Schema(description = "VLLM模型标识", example = "vllm_model_02", required = false)
    private String vllmModelId;

    @Schema(description = "语音合成模型标识", example = "tts_model_02", required = false)
    private String ttsModelId;

    @Schema(description = "音色标识", example = "voice_02", nullable = true)
    private String ttsVoiceId;

    @Schema(description = "记忆模型标识", example = "mem_model_02", nullable = true)
    private String memModelId;

    @Schema(description = "意图模型标识", example = "intent_model_02", nullable = true)
    private String intentModelId;

    @Schema(description = "插件函数信息", nullable = true)
    private List<FunctionInfo> functions;

    @Schema(description = "角色设定参数", example = "你是一个专业的客服助手，负责回答用户问题并提供帮助", nullable = true)
    private String systemPrompt;

    @Schema(description = "总结记忆", example = "构建可生长的动态记忆网络，在有限空间内保留关键信息的同时，智能维护信息演变轨迹\n"
            + "根据对话记录，总结user的重要信息，以便在未来的对话中提供更个性化的服务", nullable = true)
    private String summaryMemory;

    @Schema(description = "聊天记录配置（0不记录 1仅记录文本 2记录文本和语音）", example = "3", nullable = true)
    private Integer chatHistoryConf;

    @Schema(description = "语言编码", example = "zh_CN", nullable = true)
    private String langCode;

    @Schema(description = "交互语种", example = "中文", nullable = true)
    private String language;

    @Schema(description = "排序", example = "1", nullable = true)
    private Integer sort;

    @Data
    @Schema(description = "插件函数信息")
    public static class FunctionInfo implements Serializable {
        @Schema(description = "插件ID", example = "plugin_01")
        private String pluginId;

        @Schema(description = "函数参数信息", nullable = true)
        private HashMap<String, Object> paramInfo;

        private static final long serialVersionUID = 1L;
    }
}