package xiaozhi.modules.model.dto;

import java.io.Serializable;
import java.util.Date;

import com.baomidou.mybatisplus.annotation.FieldFill;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.extension.handlers.JacksonTypeHandler;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;
import xiaozhi.common.validator.group.UpdateGroup;

@Data
@Schema(description = "模型供应器/商")
public class ModelProviderDTO implements Serializable {
    @Schema(description = "主键")
    @NotBlank(message = "id不能为空", groups = UpdateGroup.class)
    private String id;

    @Schema(description = "模型类型(Memory/ASR/VAD/LLM/TTS)")
    @NotBlank(message = "modelType不能为空")
    private String modelType;

    @Schema(description = "供应器类型")
    @NotBlank(message = "providerCode不能为空")
    private String providerCode;

    @Schema(description = "供应器名称")
    @NotBlank(message = "name不能为空")
    private String name;

    @Schema(description = "供应器字段列表(JSON格式)")
    @TableField(typeHandler = JacksonTypeHandler.class)
    @NotBlank(message = "fields(JSON格式)不能为空")
    private String fields;

    @Schema(description = "排序")
    @NotNull(message = "sort不能为空")
    private Integer sort;

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
