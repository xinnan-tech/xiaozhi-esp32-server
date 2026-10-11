package xiaozhi.modules.agent.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
@Schema(description = "智能体快照分页查询参数")
public class AgentSnapshotPageDTO {
    @Schema(description = "当前页码，从1开始", example = "1")
    private Integer page = 1;

    @Schema(description = "每页数量", example = "10")
    private Integer limit = 10;

    @Schema(description = "版本锚点，只查询小于等于该版本号的历史快照", example = "20")
    private Integer maxVersionNo;

    public int pageOrDefault() {
        return page == null || page < 1 ? 1 : page;
    }

    public int limitOrDefault() {
        if (limit == null || limit < 1) {
            return 10;
        }
        return limit;
    }
}
