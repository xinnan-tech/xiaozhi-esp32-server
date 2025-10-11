package xiaozhi.modules.voiceclone.entity;

import java.util.Date;

import com.baomidou.mybatisplus.annotation.FieldFill;
import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import lombok.EqualsAndHashCode;

@Data
@EqualsAndHashCode(callSuper = false)
@TableName("ai_voice_clone")
@Schema(description = "声音克隆")
public class VoiceCloneEntity {

    @TableId(type = IdType.ASSIGN_UUID)
    @Schema(description = "唯一标识")
    private String id;

    @Schema(description = "声音名称")
    private String name;

    @Schema(description = "模型id")
    private String modelId;

    @Schema(description = "声音id")
    private String voiceId;

    @Schema(description = "用户 ID（关联用户表）")
    private Long userId;

    @Schema(description = "声音")
    private byte[] voice;

    @Schema(description = "训练状态：0待训练 1训练中 2训练成功 3训练失败")
    private Integer trainStatus;

    @Schema(description = "训练错误原因")
    private String trainError;

    @Schema(description = "创建者")
    @TableField(fill = FieldFill.INSERT)
    private Long creator;

    @Schema(description = "创建时间")
    @TableField(fill = FieldFill.INSERT)
    private Date createDate;
}
