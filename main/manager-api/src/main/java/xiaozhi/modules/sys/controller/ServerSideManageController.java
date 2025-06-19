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
import xiaozhi.modules.device.entity.DeviceCommandEntity;
import xiaozhi.modules.device.service.DeviceCommandService;
import xiaozhi.modules.sys.dto.EmitCommandDTO;
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
    private final DeviceCommandService deviceCommandService; // 新增注入
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

    @Operation(summary = "通过WebSocket发送指令")
    @PostMapping("/emit-command")
    @LogOperation("通过WebSocket发送指令")
    // @RequiresPermissions("sys:role:superAdmin")
    public Result<DeviceCommandEntity> emitCommand(@RequestBody @Valid EmitCommandDTO dto) {
        String wsText = sysParamsService.getValue(Constant.SERVER_WEBSOCKET, true);
        if (StringUtils.isBlank(wsText)) {
            throw new RenException("未配置服务端WebSocket地址");
        }
        String targetWs = dto.getTargetWs();
        String[] wsList = wsText.split(";");
        if (StringUtils.isBlank(targetWs) || !Arrays.asList(wsList).contains(targetWs)) {
            throw new RenException("目标WebSocket地址不存在");
        }
        return new Result<DeviceCommandEntity>().ok(emitCommandByWs(targetWs, dto));
    }

    private DeviceCommandEntity emitCommandByWs(String targetWsUri, EmitCommandDTO dto) {
        if (StringUtils.isBlank(targetWsUri) || dto == null || StringUtils.isBlank(dto.getCommand())) {
            return null;
        }
        String serverSK = sysParamsService.getValue(Constant.SERVER_SECRET, true);
        WebSocketHttpHeaders headers = new WebSocketHttpHeaders();
        headers.add("device-id", UUID.randomUUID().toString());
        headers.add("client-id", UUID.randomUUID().toString());

        final DeviceCommandEntity[] resultEntity = { null };
        try (WebSocketClientManager client = new WebSocketClientManager.Builder()
                .connectTimeout(3, TimeUnit.SECONDS)
                .maxSessionDuration(120, TimeUnit.SECONDS)
                .uri(targetWsUri)
                .headers(headers)
                .build()) {
            // 发送command类型指令
            Map<String, Object> payload = new HashMap<>();
            payload.put("secret", serverSK);
            payload.put("command", dto.getCommand());
            payload.put("deviceId", dto.getDeviceId());
            client.sendJson(ServerActionPayloadDTO.build(ServerActionEnum.COMMAND, payload));
            // 监听返回
            client.listener((jsonText) -> {
                if (StringUtils.isBlank(jsonText)) {
                    return false;
                }
                try {
                    Map<String, Object> resp = objectMapper.readValue(jsonText, Map.class);
                    Object status = resp.get("status");
                    if ("success".equals(status) || "fail".equals(status)) {
                        DeviceCommandEntity entity = new DeviceCommandEntity();
                        entity.setDeviceId(dto.getDeviceId());
                        entity.setCommandContent(dto.getCommand());
                        entity.setCommandType("message");
                        entity.setIsExecuted("success".equals(status) ? 1 : 0);
                        deviceCommandService.addCommand(entity);
                        resultEntity[0] = entity;
                        return true;
                    }
                } catch (Exception e) {
                    // ignore
                }
                return false;
            });
        } catch (Exception e) {
            throw new RenException("WebSocket连接失败或连接超时");
        }
        return resultEntity[0];
    }

    @Operation(summary = "查询设备是否在线")
    @PostMapping("/device-online")
    @LogOperation("查询设备是否在线")
    public Result<Boolean> checkDeviceOnline(@RequestBody Map<String, String> params) {
        String deviceId = params.get("deviceId");
        String targetWs = params.get("targetWs");
        if (StringUtils.isBlank(deviceId) || StringUtils.isBlank(targetWs)) {
            throw new RenException("参数缺失");
        }
        String wsText = sysParamsService.getValue(Constant.SERVER_WEBSOCKET, true);
        if (StringUtils.isBlank(wsText)) {
            throw new RenException("未配置服务端WebSocket地址");
        }
        String[] wsList = wsText.split(";");
        if (!Arrays.asList(wsList).contains(targetWs)) {
            throw new RenException("目标WebSocket地址不存在");
        }
        return new Result<Boolean>().ok(checkDeviceOnlineByWs(targetWs, deviceId));
    }

    private Boolean checkDeviceOnlineByWs(String targetWsUri, String deviceId) {
        if (StringUtils.isBlank(targetWsUri) || StringUtils.isBlank(deviceId)) {
            return false;
        }
        String serverSK = sysParamsService.getValue(Constant.SERVER_SECRET, true);
        WebSocketHttpHeaders headers = new WebSocketHttpHeaders();
        headers.add("device-id", UUID.randomUUID().toString());
        headers.add("client-id", UUID.randomUUID().toString());

        final boolean[] online = { false };
        try (WebSocketClientManager client = new WebSocketClientManager.Builder()
                .connectTimeout(3, TimeUnit.SECONDS)
                .maxSessionDuration(30, TimeUnit.SECONDS)
                .uri(targetWsUri)
                .headers(headers)
                .build()) {
            // 发送CHECK_ONLINE类型指令
            Map<String, Object> payload = new HashMap<>();
            payload.put("secret", serverSK);
            payload.put("deviceId", deviceId);
            client.sendJson(ServerActionPayloadDTO.build(ServerActionEnum.CHECK_ONLINE, payload));
            // 监听返回
            client.listener((jsonText) -> {
                if (StringUtils.isBlank(jsonText)) {
                    return false;
                }
                try {
                    Map<String, Object> resp = objectMapper.readValue(jsonText, Map.class);
                    Object status = resp.get("status");
                    Object onlineVal = resp.get("online");
                    if ("success".equals(status) && onlineVal instanceof Boolean) {
                        online[0] = (Boolean) onlineVal;
                        return true;
                    }
                } catch (Exception e) {
                    // ignore
                }
                return false;
            });
        } catch (Exception e) {
            throw new RenException("WebSocket连接失败或连接超时");
        }
        return online[0];
    }
}
