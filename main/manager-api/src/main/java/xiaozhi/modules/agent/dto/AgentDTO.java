package xiaozhi.modules.agent.dto;

import java.util.Date;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

/**
 * 智能体数据传输对象
 * 用于在服务层和控制器层之间传递智能体相关的数据
 */
@Data
@Schema(description = "智能体对象")
public class AgentDTO {
    @Schema(description = "智能体编码", example = "AGT_1234567890")
    private String id;

    @Schema(description = "智能体名称", example = "客服助手")
    private String agentName;

    @Schema(description = "语音合成模型名称", example = "tts_model_01")
    private String ttsModelName;

    @Schema(description = "音色名称", example = "voice_01")
    private String ttsVoiceName;

    @Schema(description = "大语言模型名称", example = "llm_model_01")
    private String llmModelName;

    @Schema(description = "角色设定参数", example = "你是一个专业的客服助手，负责回答用户问题并提供帮助")
    private String systemPrompt;

    @Schema(description = "最后连接时间", example = "2024-03-20 10:00:00")
    private Date lastConnectedAt;

    @Schema(description = "设备数量", example = "10")
    private Integer deviceCount;
}