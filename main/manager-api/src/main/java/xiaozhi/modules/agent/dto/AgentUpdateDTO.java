package xiaozhi.modules.agent.dto;

import java.io.Serializable;

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

    @Schema(description = "智能体编码", example = "AGT_1234567890", required = false)
    private String agentCode;

    @Schema(description = "智能体名称", example = "客服助手", required = false)
    private String agentName;

    @Schema(description = "语音识别模型标识", example = "asr_model_02", required = false)
    private String asrModelId;

    @Schema(description = "语音活动检测标识", example = "vad_model_02", required = false)
    private String vadModelId;

    @Schema(description = "大语言模型标识", example = "llm_model_02", required = false)
    private String llmModelId;

    @Schema(description = "语音合成模型标识", example = "tts_model_02", required = false)
    private String ttsModelId;

    @Schema(description = "音色标识", example = "voice_02", required = false)
    private String ttsVoiceId;

    @Schema(description = "记忆模型标识", example = "mem_model_02", required = false)
    private String memModelId;

    @Schema(description = "意图模型标识", example = "intent_model_02", required = false)
    private String intentModelId;

    @Schema(description = "角色设定参数", example = "你是一个专业的客服助手，负责回答用户问题并提供帮助", required = false)
    private String systemPrompt;

    @Schema(description = "语言编码", example = "zh_CN", required = false)
    private String langCode;

    @Schema(description = "交互语种", example = "中文", required = false)
    private String language;

    @Schema(description = "排序", example = "1", required = false)
    private Integer sort;
}