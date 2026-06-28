package xiaozhi.modules.feedback.vo;

import java.io.Serializable;
import java.util.Date;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
@Schema(description = "门店信息")
public class StoreVO implements Serializable {

    @Schema(description = "门店ID")
    private String id;

    @Schema(description = "6位门店码")
    private String storeCode;

    @Schema(description = "门店名称")
    private String storeName;

    @Schema(description = "店长")
    private String manager;

    @Schema(description = "股东(逗号分隔)")
    private String shareholders;

    @Schema(description = "绑定的智能体ID")
    private String agentId;

    @Schema(description = "状态 0禁用 1启用")
    private Integer status;

    @Schema(description = "创建时间")
    private Date createDate;
}
