package xiaozhi.modules.agent.dto;

import java.io.Serializable;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

/**
 * 智能体记忆更新DTO
 */
@Data
@Schema(description = "智能体记忆更新对象")
public class AgentMemoryDTO implements Serializable {
    private static final long serialVersionUID = 1L;

    @Schema(description = "总结记忆", example = "构建可生长的动态记忆网络，在有限空间内保留关键信息的同时，智能维护信息演变轨迹\n" +
            "根据对话记录，总结user的重要信息，以便在未来的对话中提供更个性化的服务", required = false)
    private String summaryMemory;
}