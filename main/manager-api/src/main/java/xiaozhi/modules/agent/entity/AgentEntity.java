package xiaozhi.modules.agent.entity;

import java.util.Date;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
@TableName("ai_agent")
@Schema(description = "智能体信息")
public class AgentEntity {

    @TableId(type = IdType.ASSIGN_UUID)
    @Schema(description = "智能体唯一标识")
    private String id;

    @Schema(description = "所属用户ID")
    private Long userId;

    @Schema(description = "智能体编码")
    private String agentCode;

    @Schema(description = "智能体名称")
    private String agentName;

    @Schema(description = "语音识别模型标识")
    private String asrModelId;

    @Schema(description = "语音活动检测标识")
    private String vadModelId;

    @Schema(description = "大语言模型标识")
    private String llmModelId;

    @Schema(description = "语音合成模型标识")
    private String ttsModelId;

    @Schema(description = "音色标识")
    private String ttsVoiceId;

    @Schema(description = "记忆模型标识")
    private String memModelId;

    @Schema(description = "意图模型标识")
    private String intentModelId;

    @Schema(description = "聊天记录配置（0不记录 1仅记录文本 2记录文本和语音）")
    private Integer chatHistoryConf;

    @Schema(description = "角色设定参数")
    private String systemPrompt;

    @Schema(description = "语言编码")
    private String langCode;

    @Schema(description = "交互语种")
    private String language;

    @Schema(description = "排序")
    private Integer sort;

    @Schema(description = "创建者")
    private Long creator;

    @Schema(description = "创建时间")
    private Date createdAt;

    @Schema(description = "更新者")
    private Long updater;

    @Schema(description = "更新时间")
    private Date updatedAt;
}