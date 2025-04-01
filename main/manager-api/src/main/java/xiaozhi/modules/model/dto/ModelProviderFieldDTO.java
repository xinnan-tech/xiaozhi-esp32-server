package xiaozhi.modules.model.dto;

import java.io.Serializable;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
@Schema(description = "模型供应器字段")
public class ModelProviderFieldDTO implements Serializable {
    @Schema(description = "字段名")
    private String key;

    @Schema(description = "字段标签")
    private String label;

    @Schema(description = "字段类型")
    private String type;
}
