package xiaozhi.modules.agent.entity;

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
@TableName("ai_agent_ext")
@Schema(description = "agent 扩展字段")
public class AgentExtEntity {

    @TableId(type = IdType.INPUT)
    @Schema(description = "关联 agent(主键,即 agent.id)")
    private String agentId;

    @Schema(description = "扩展字段 JSON 对象 {key:value}")
    private String extJson;

    @TableField(fill = FieldFill.INSERT)
    private Long creator;

    @TableField(fill = FieldFill.INSERT)
    private Date createDate;

    @TableField(fill = FieldFill.UPDATE)
    private Long updater;

    @TableField(fill = FieldFill.UPDATE)
    private Date updateDate;
}
