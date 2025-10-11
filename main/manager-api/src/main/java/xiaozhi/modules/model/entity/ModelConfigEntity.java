package xiaozhi.modules.model.entity;

import java.util.Date;

import com.baomidou.mybatisplus.annotation.FieldFill;
import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.baomidou.mybatisplus.extension.handlers.JacksonTypeHandler;

import cn.hutool.json.JSONObject;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
@TableName(value = "ai_model_config", autoResultMap = true)
@Schema(description = "モデル設定テーブル")
public class ModelConfigEntity {

    @TableId(type = IdType.ASSIGN_UUID)
    @Schema(description = "主キー")
    private String id;

    @Schema(description = "モデルタイプ(Memory/ASR/VAD/LLM/TTS)")
    private String modelType;

    @Schema(description = "モデルコード(例：AliLLM、DoubaoTTS)")
    private String modelCode;

    @Schema(description = "モデル名")
    private String modelName;

    @Schema(description = "デフォルト設定かどうか(0:いいえ 1:はい)")
    private Integer isDefault;

    @Schema(description = "有効かどうか")
    private Integer isEnabled;

    @TableField(typeHandler = JacksonTypeHandler.class)
    @Schema(description = "モデル設定(JSON形式)")
    private JSONObject configJson;

    @Schema(description = "公式ドキュメントリンク")
    private String docLink;

    @Schema(description = "備考")
    private String remark;

    @Schema(description = "ソート順")
    private Integer sort;

    @Schema(description = "更新者")
    @TableField(fill = FieldFill.UPDATE)
    private Long updater;

    @Schema(description = "更新時間")
    @TableField(fill = FieldFill.UPDATE)
    private Date updateDate;

    @Schema(description = "作成者")
    @TableField(fill = FieldFill.INSERT)
    private Long creator;

    @Schema(description = "作成時間")
    @TableField(fill = FieldFill.INSERT)
    private Date createDate;
}
