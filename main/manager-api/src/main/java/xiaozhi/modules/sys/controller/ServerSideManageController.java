package xiaozhi.modules.sys.controller;

import java.util.*;
import java.util.concurrent.TimeUnit;

import org.apache.commons.lang3.StringUtils;
import org.apache.shiro.authz.annotation.RequiresPermissions;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.socket.WebSocketHttpHeaders;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.AllArgsConstructor;
import xiaozhi.common.annotation.LogOperation;
import xiaozhi.common.constant.Constant;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.utils.Result;
import xiaozhi.modules.sys.dto.EmitSeverActionDTO;
import xiaozhi.modules.sys.dto.ServerActionPayloadDTO;
import xiaozhi.modules.sys.dto.ServerActionResponseDTO;
import xiaozhi.modules.sys.enums.ServerActionEnum;
import xiaozhi.modules.sys.service.SysParamsService;
import xiaozhi.modules.sys.utils.WebSocketClientManager;

/**
 * 服务端管理控制器
 */
@RestController
@RequestMapping("/admin/server")
@Tag(name = "服务端管理")
@AllArgsConstructor
public class ServerSideManageController {
    private final SysParamsService sysParamsService;
    private static final ObjectMapper objectMapper;
    static {
        objectMapper = new ObjectMapper();
        // 忽略json字符串中存在，但pojo中不存在对应字段的情况
        objectMapper.configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);
    }

    @Operation(summary = "获取Ws服务端列表")
    @GetMapping("/server-list")
    @RequiresPermissions("sys:role:superAdmin")
    public Result<List<String>> getWsServerList() {
        String wsText = sysParamsService.getValue(Constant.SERVER_WEBSOCKET, true);
        if (StringUtils.isBlank(wsText)) {
            return new Result<List<String>>().ok(Collections.emptyList());
        }
        return new Result<List<String>>().ok(Arrays.asList(wsText.split(";")));
    }

    @Operation(summary = "通知python服务端更新配置")
    @PostMapping("/emit-action")
    @LogOperation("通知python服务端更新配置")
    @RequiresPermissions("sys:role:superAdmin")
    public Result<Boolean> emitServerAction(@RequestBody @Valid EmitSeverActionDTO emitSeverActionDTO) {
        if (emitSeverActionDTO.getAction() == null) {
            throw new RenException("无效服务端操作");
        }
        String wsText = sysParamsService.getValue(Constant.SERVER_WEBSOCKET, true);
        if (StringUtils.isBlank(wsText)) {
            throw new RenException("未配置服务端WebSocket地址");
        }
        String targetWs = emitSeverActionDTO.getTargetWs();
        String[] wsList = wsText.split(";");
        // 找到需要发起的
        if (StringUtils.isBlank(targetWs) || !Arrays.asList(wsList).contains(targetWs)) {
            throw new RenException("目标WebSocket地址不存在");
        }
        return new Result<Boolean>().ok(emitServerActionByWs(targetWs, emitSeverActionDTO.getAction()));
    }

    private Boolean emitServerActionByWs(String targetWsUri, ServerActionEnum actionEnum) {
        if (StringUtils.isBlank(targetWsUri) || actionEnum == null) {
            return false;
        }
        String serverSK = sysParamsService.getValue(Constant.SERVER_SECRET, true);
        WebSocketHttpHeaders headers = new WebSocketHttpHeaders();
        headers.add("device-id", UUID.randomUUID().toString());
        headers.add("client-id", UUID.randomUUID().toString());

        try (WebSocketClientManager client = new WebSocketClientManager.Builder()
                .connectTimeout(3, TimeUnit.SECONDS)
                .maxSessionDuration(120, TimeUnit.SECONDS)
                .uri(targetWsUri)
                .headers(headers)
                .build()) {
            // 如果连接成功则发送一个json数据包并等待服务端响应
            client.sendJson(
                    ServerActionPayloadDTO.build(
                            actionEnum,
                            Map.of("secret", serverSK)));
            // 等待服务端响应并持续监听信息
            client.listener((jsonText) -> {
                if (StringUtils.isBlank(jsonText)) {
                    return false;
                }
                try {
                    ServerActionResponseDTO response = objectMapper.readValue(jsonText, ServerActionResponseDTO.class);
                    Boolean isSuccess = ServerActionResponseDTO.isSuccess(response);
                    return isSuccess;
                } catch (JsonProcessingException e) {
                    return false;
                }
            });
        } catch (Exception e) {
            // 捕获全部错误，由全局异常处理器返回
            throw new RenException("WebSocket连接失败或连接超时");
        }
        return true;
    }
}
