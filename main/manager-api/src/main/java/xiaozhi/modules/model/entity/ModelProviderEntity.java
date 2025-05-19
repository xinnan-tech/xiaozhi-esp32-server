package xiaozhi.modules.model.entity;

import java.util.Date;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
@TableName("ai_model_provider")
@Schema(description = "模型供应器表")
public class ModelProviderEntity {

    @TableId(type = IdType.ASSIGN_UUID)
    @Schema(description = "主键")
    private String id;

    @Schema(description = "模型类型(Memory/ASR/VAD/LLM/TTS)")
    private String modelType;

    @Schema(description = "供应器类型，如 openai、")
    private String providerCode;

    @Schema(description = "供应器名称")
    private String name;

    @Schema(description = "供应器字段列表(JSON格式)")
    private String fields;

    @Schema(description = "排序")
    private Integer sort;

    @Schema(description = "创建者")
    private Long creator;

    @Schema(description = "创建时间")
    private Date createDate;

    @Schema(description = "更新者")
    private Long updater;

    @Schema(description = "更新时间")
    private Date updateDate;
}
