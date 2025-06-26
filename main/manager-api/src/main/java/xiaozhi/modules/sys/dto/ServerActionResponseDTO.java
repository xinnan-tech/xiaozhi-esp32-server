package xiaozhi.modules.sys.dto;

import lombok.Data;
import xiaozhi.modules.sys.enums.ServerActionResponseEnum;

import java.util.Map;

/**
 * 服务端动作响应体
 */
@Data
public class ServerActionResponseDTO
{
    private ServerActionResponseEnum status;
    private String message;
    private String type;
    private Map<String, Object> content; // 后续这个字段可以移除，并把这个类作为基类，针对业务写自己的content类型
    public static final String DEFAULT_TYPE_FORM_SERVER = "server";

    public static Boolean isSuccess(ServerActionResponseDTO actionResponseDTO) {
        System.out.println(actionResponseDTO);
        if (actionResponseDTO == null) {
            return false;
        }
        if (actionResponseDTO.getStatus() == null || !actionResponseDTO.getStatus().equals(ServerActionResponseEnum.SUCCESS)) {
            return false;
        }
        Object actionType = actionResponseDTO.getContent().get("action");
        if (actionType == null) {
            return false;
        }
        return actionResponseDTO.getType() != null && actionResponseDTO.getType().equals(DEFAULT_TYPE_FORM_SERVER);
    }
}
