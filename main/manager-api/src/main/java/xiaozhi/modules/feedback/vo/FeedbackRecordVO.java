package xiaozhi.modules.feedback.vo;

import java.io.Serializable;
import java.util.Date;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
@Schema(description = "反馈记录信息")
public class FeedbackRecordVO implements Serializable {

    @Schema(description = "记录ID")
    private String id;

    @Schema(description = "WebSocket会话ID")
    private String sessionId;

    @Schema(description = "门店ID")
    private String storeId;

    @Schema(description = "员工ID")
    private String employeeId;

    @Schema(description = "设备MAC")
    private String deviceMac;

    @Schema(description = "ASR原始文本")
    private String rawAsrText;

    @Schema(description = "规整后文本")
    private String cleanedText;

    @Schema(description = "QA问答JSON")
    private String qaJson;

    @Schema(description = "标准版好评")
    private String reviewLong;

    @Schema(description = "精简短评")
    private String reviewShort;

    @Schema(description = "状态 0无效 1有效")
    private Integer status;

    @Schema(description = "创建时间")
    private Date createDate;
}
