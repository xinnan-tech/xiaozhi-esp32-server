package xiaozhi.modules.sys.dto;

import lombok.Data;
import xiaozhi.modules.sys.enums.ServerActionEnum;

import java.util.Map;

/**
 * 服务端动作DTO
 */
@Data
public class ServerActionPayloadDTO
{
    /**
    * 类型（智控台发往服务端的都是server）
    */
    private String type;
    /**
    * 动作
    */
    private ServerActionEnum action;
    /**
    * 内容
    */
    private Map<String, Object> content;

    public static ServerActionPayloadDTO build(ServerActionEnum action, Map<String, Object> content) {
        ServerActionPayloadDTO serverActionPayloadDTO = new ServerActionPayloadDTO();
        serverActionPayloadDTO.setAction(action);
        serverActionPayloadDTO.setContent(content);
        serverActionPayloadDTO.setType("server");
        return serverActionPayloadDTO;
    }
    // 私有化
    private ServerActionPayloadDTO() {}
}
