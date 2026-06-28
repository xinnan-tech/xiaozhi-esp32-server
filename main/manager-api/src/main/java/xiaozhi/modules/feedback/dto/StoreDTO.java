package xiaozhi.modules.feedback.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
@Schema(description = "门店信息")
public class StoreDTO {

    @Schema(description = "门店名称")
    @NotBlank(message = "{store.storeName.require}")
    private String storeName;

    @Schema(description = "店长")
    private String manager;

    @Schema(description = "股东(逗号分隔)")
    private String shareholders;

    @Schema(description = "绑定的智能体ID")
    private String agentId;
}
