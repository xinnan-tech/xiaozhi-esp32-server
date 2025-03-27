package xiaozhi.modules.agent.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

import java.io.Serializable;

/**
 * 智能体创建DTO
 * 专用于新增智能体，不包含id、agentCode和sort字段，这些字段由系统自动生成/设置默认值
 */
@Data
@Schema(description = "智能体创建对象")
public class AgentCreateDTO implements Serializable {
    private static final long serialVersionUID = 1L;
    
    @Schema(description = "智能体名称", example = "客服助手")
    @NotBlank(message = "智能体名称不能为空")
    private String agentName;
    
    @Schema(description = "语音识别模型标识", example = "asr_model_01")
    private String asrModelId;
    
    @Schema(description = "语音活动检测标识", example = "vad_model_01")
    private String vadModelId;
    
    @Schema(description = "大语言模型标识", example = "llm_model_01")
    private String llmModelId;
    
    @Schema(description = "语音合成模型标识", example = "tts_model_01")
    private String ttsModelId;
    
    @Schema(description = "音色标识", example = "voice_01")
    private String ttsVoiceId;
    
    @Schema(description = "记忆模型标识", example = "mem_model_01")
    private String memModelId;
    
    @Schema(description = "意图模型标识", example = "intent_model_01")
    private String intentModelId;
    
    @Schema(description = "角色设定参数", example = "你是一个专业的客服助手，负责回答用户问题")
    private String systemPrompt;
    
    @Schema(description = "语言编码", example = "zh_CN")
    private String langCode;
    
    @Schema(description = "交互语种", example = "中文")
    private String language;
} 