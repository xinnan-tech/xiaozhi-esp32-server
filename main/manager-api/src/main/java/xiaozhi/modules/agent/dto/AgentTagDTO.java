package xiaozhi.modules.agent.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.io.Serializable;
import java.util.List;

@Data
@Schema(description = "智能体标签DTO")
public class AgentTagDTO implements Serializable {

    private static final long serialVersionUID = 1L;

    @Schema(description = "标签ID")
    private String id;

    @Schema(description = "标签名称")
    private String tagName;
}
