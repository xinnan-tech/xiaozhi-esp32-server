package xiaozhi.modules.device.controller;

import java.util.List;

import org.apache.commons.lang3.StringUtils;
import org.apache.shiro.authz.annotation.RequiresPermissions;
import org.springframework.beans.BeanUtils;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.RestTemplate;

import com.fasterxml.jackson.databind.ObjectMapper;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.redis.RedisKeys;
import xiaozhi.common.redis.RedisUtils;
import xiaozhi.common.user.UserDetail;
import xiaozhi.common.utils.Result;
import xiaozhi.modules.device.dto.DeviceManualAddDTO;
import xiaozhi.modules.device.dto.DeviceRegisterDTO;
import xiaozhi.modules.device.dto.DeviceUnBindDTO;
import xiaozhi.modules.device.dto.DeviceUpdateDTO;
import xiaozhi.modules.device.entity.DeviceEntity;
import xiaozhi.modules.device.service.DeviceService;
import xiaozhi.modules.security.user.SecurityUser;
import xiaozhi.modules.sys.service.SysParamsService;

@Tag(name = "设备管理")
@RestController
@RequestMapping("/device")
public class DeviceController {
    private final DeviceService deviceService;
    private final RedisUtils redisUtils;
    private final SysParamsService sysParamsService;
    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper;

    public DeviceController(DeviceService deviceService, RedisUtils redisUtils, SysParamsService sysParamsService,
            RestTemplate restTemplate, ObjectMapper objectMapper) {
        this.deviceService = deviceService;
        this.redisUtils = redisUtils;
        this.sysParamsService = sysParamsService;
        this.restTemplate = restTemplate;
        this.objectMapper = objectMapper;
    }

    @PostMapping("/bind/{agentId}/{deviceCode}")
    @Operation(summary = "绑定设备")
    @RequiresPermissions("sys:role:normal")
    public Result<Void> bindDevice(@PathVariable String agentId, @PathVariable String deviceCode) {
        deviceService.deviceActivation(agentId, deviceCode);
        return new Result<>();
    }

    @PostMapping("/register")
    @Operation(summary = "注册设备")
    public Result<String> registerDevice(@RequestBody DeviceRegisterDTO deviceRegisterDTO) {
        String macAddress = deviceRegisterDTO.getMacAddress();
        if (StringUtils.isBlank(macAddress)) {
            return new Result<String>().error(ErrorCode.NOT_NULL, "mac地址不能为空");
        }
        // 生成六位验证码
        String code = String.valueOf(Math.random()).substring(2, 8);
        String key = RedisKeys.getDeviceCaptchaKey(code);
        String existsMac = null;
        do {
            existsMac = (String) redisUtils.get(key);
        } while (StringUtils.isNotBlank(existsMac));

        redisUtils.set(key, macAddress);
        return new Result<String>().ok(code);
    }

    @GetMapping("/bind/{agentId}")
    @Operation(summary = "获取已绑定设备")
    @RequiresPermissions("sys:role:normal")
    public Result<List<DeviceEntity>> getUserDevices(@PathVariable String agentId) {
        UserDetail user = SecurityUser.getUser();
        List<DeviceEntity> devices = deviceService.getUserDevices(user.getId(), agentId);
        return new Result<List<DeviceEntity>>().ok(devices);
    }

    @PostMapping("/bind/{agentId}")
    @Operation(summary = "设备在线接口")
    @RequiresPermissions("sys:role:normal")
    public Result<String> forwardToMqttGateway(@PathVariable String agentId, @RequestBody String requestBody) {
        try {
            // 从系统参数中获取MQTT网关地址
            String mqttGatewayUrl = sysParamsService.getValue("server.mqtt_manager_api", true);
            if (StringUtils.isBlank(mqttGatewayUrl) || "null".equals(mqttGatewayUrl)) {
                return new Result<>();
            }

            // 获取当前用户的设备列表
            UserDetail user = SecurityUser.getUser();
            List<DeviceEntity> devices = deviceService.getUserDevices(user.getId(), agentId);

            // 构建deviceIds数组
            java.util.List<String> deviceIds = new java.util.ArrayList<>();
            for (DeviceEntity device : devices) {
                String macAddress = device.getMacAddress() != null ? device.getMacAddress() : "unknown";
                String groupId = device.getBoard() != null ? device.getBoard() : "GID_default";

                // 替换冒号为下划线
                groupId = groupId.replace(":", "_");
                macAddress = macAddress.replace(":", "_");

                // 构建mqtt客户端ID格式：groupId@@@macAddress@@@macAddress
                String mqttClientId = groupId + "@@@" + macAddress + "@@@" + macAddress;
                deviceIds.add(mqttClientId);
            }

            // 构建完整的URL
            String url = "http://" + mqttGatewayUrl + "/api/devices/status";

            // 设置请求头
            HttpHeaders headers = new HttpHeaders();
            headers.set("Content-Type", "application/json");

            // 生成Bearer令牌
            String token = generateBearerToken();
            if (token == null) {
                return new Result<String>().error("令牌生成失败");
            }
            headers.set("Authorization", "Bearer " + token);

            // 构建请求体JSON
            String jsonBody = "{\"clientIds\":" + objectMapper.writeValueAsString(deviceIds) + "}";
            HttpEntity<String> requestEntity = new HttpEntity<>(jsonBody, headers);

            // 发送POST请求
            ResponseEntity<String> response = restTemplate.exchange(url, HttpMethod.POST, requestEntity, String.class);

            // 返回响应
            return new Result<String>().ok(response.getBody());
        } catch (Exception e) {
            return new Result<String>().error("转发请求失败: " + e.getMessage());
        }
    }

    private String generateBearerToken() {
        try {
            // 获取当前日期，格式为yyyy-MM-dd
            String dateStr = java.time.LocalDate.now()
                    .format(java.time.format.DateTimeFormatter.ofPattern("yyyy-MM-dd"));

            // 获取MQTT签名密钥
            String signatureKey = sysParamsService.getValue("server.mqtt_signature_key", false);
            if (StringUtils.isBlank(signatureKey)) {
                return null;
            }

            // 将日期字符串与MQTT_SIGNATURE_KEY连接
            String tokenContent = dateStr + signatureKey;

            // 对连接后的字符串进行SHA256哈希计算
            String token = org.apache.commons.codec.digest.DigestUtils.sha256Hex(tokenContent);

            return token;
        } catch (Exception e) {
            return null;
        }
    }

    @PostMapping("/unbind")
    @Operation(summary = "解绑设备")
    @RequiresPermissions("sys:role:normal")
    public Result<Void> unbindDevice(@RequestBody DeviceUnBindDTO unDeviveBind) {
        UserDetail user = SecurityUser.getUser();
        deviceService.unbindDevice(user.getId(), unDeviveBind.getDeviceId());
        return new Result<Void>();
    }

    @PutMapping("/update/{id}")
    @Operation(summary = "更新设备信息")
    @RequiresPermissions("sys:role:normal")
    public Result<Void> updateDeviceInfo(@PathVariable String id, @Valid @RequestBody DeviceUpdateDTO deviceUpdateDTO) {
        DeviceEntity entity = deviceService.selectById(id);
        if (entity == null) {
            return new Result<Void>().error("设备不存在");
        }
        UserDetail user = SecurityUser.getUser();
        if (!entity.getUserId().equals(user.getId())) {
            return new Result<Void>().error("设备不存在");
        }
        BeanUtils.copyProperties(deviceUpdateDTO, entity);
        deviceService.updateById(entity);
        return new Result<Void>();
    }

    @PostMapping("/manual-add")
    @Operation(summary = "手动添加设备")
    @RequiresPermissions("sys:role:normal")
    public Result<Void> manualAddDevice(@RequestBody @Valid DeviceManualAddDTO dto) {
        UserDetail user = SecurityUser.getUser();
        deviceService.manualAddDevice(user.getId(), dto);
        return new Result<>();
    }
}