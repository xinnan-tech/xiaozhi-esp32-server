package xiaozhi.modules.sys.vo;

import java.io.Serializable;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

/**
 * 字典数据VO
 */
@Data
@Schema(description = "字典数据项")
public class SysDictDataItem implements Serializable {

    @Schema(description = "字典标签")
    private String name;

    @Schema(description = "字典值")
    private String key;
}
