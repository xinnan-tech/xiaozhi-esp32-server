package xiaozhi.modules.feedback.entity;

import java.util.Date;

import com.baomidou.mybatisplus.annotation.FieldFill;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableName;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import lombok.EqualsAndHashCode;

@Data
@EqualsAndHashCode(callSuper = false)
@TableName("feedback_store")
@Schema(description = "门店信息")
public class StoreEntity {

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

    @Schema(description = "更新者")
    @TableField(fill = FieldFill.UPDATE)
    private Long updater;

    @Schema(description = "更新时间")
    @TableField(fill = FieldFill.UPDATE)
    private Date updateDate;

    @Schema(description = "创建者")
    @TableField(fill = FieldFill.INSERT)
    private Long creator;

    @Schema(description = "创建时间")
    @TableField(fill = FieldFill.INSERT)
    private Date createDate;
}
