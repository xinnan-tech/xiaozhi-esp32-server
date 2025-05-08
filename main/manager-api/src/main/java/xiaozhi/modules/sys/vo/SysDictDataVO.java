package xiaozhi.modules.sys.vo;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.io.Serializable;
import java.util.Date;

/**
 * 字典数据VO
 */
@Data
@Schema(description = "字典数据VO")
public class SysDictDataVO implements Serializable {
    @Schema(description = "主键")
    private Long id;

    @Schema(description = "字典类型ID")
    private Long dictTypeId;

    @Schema(description = "字典标签")
    private String dictLabel;

    @Schema(description = "字典值")
    private String dictValue;

    @Schema(description = "备注")
    private String remark;

    @Schema(description = "排序")
    private Integer sort;

    @Schema(description = "创建者")
    private Long creator;

    @Schema(description = "创建者名称")
    private String creatorName;

    @Schema(description = "创建时间")
    private Date createDate;

    @Schema(description = "更新者")
    private Long updater;

    @Schema(description = "更新者名称")
    private String updaterName;

    @Schema(description = "更新时间")
    private Date updateDate;
}
