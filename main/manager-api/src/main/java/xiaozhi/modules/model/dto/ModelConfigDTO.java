package xiaozhi.modules.model.dto;

import java.io.Serial;
import java.io.Serializable;

import cn.hutool.json.JSONObject;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
@Schema(description = "模型供应器/商")
public class ModelConfigDTO implements Serializable {

    @Serial
    private static final long serialVersionUID = 1L;

    @Schema(description = "主键")
    private String id;

    @Schema(description = "模型类型(Memory/ASR/VAD/LLM/TTS)")
    private String modelType;

    @Schema(description = "模型编码(如AliLLM、DoubaoTTS)")
    private String modelCode;

    @Schema(description = "模型名称")
    private String modelName;

    @Schema(description = "是否默认配置(0否 1是)")
    private Integer isDefault;

    @Schema(description = "是否启用")
    private Integer isEnabled;

    @Schema(description = "模型配置(JSON格式)")
    private JSONObject configJson;

    @Schema(description = "官方文档链接")
    private String docLink;

    @Schema(description = "备注")
    private String remark;

    @Schema(description = "排序")
    private Integer sort;
}
