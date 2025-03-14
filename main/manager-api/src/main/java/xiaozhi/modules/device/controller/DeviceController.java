package xiaozhi.modules.device.controller;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.Parameters;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.AllArgsConstructor;
import org.apache.commons.lang3.StringUtils;
import org.apache.shiro.authz.annotation.RequiresPermissions;
import org.springframework.web.bind.annotation.*;
import xiaozhi.common.constant.Constant;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.page.PageData;
import xiaozhi.common.redis.RedisKeys;
import xiaozhi.common.redis.RedisUtils;
import xiaozhi.common.user.UserDetail;
import xiaozhi.common.utils.JsonUtils;
import xiaozhi.common.utils.Result;
import xiaozhi.modules.device.dto.DeviceHeaderDTO;
import xiaozhi.modules.device.dto.DeviceUnBindDTO;
import xiaozhi.modules.device.entity.DeviceEntity;
import xiaozhi.modules.device.service.DeviceService;
import xiaozhi.modules.security.user.SecurityUser;

import java.util.List;
import java.util.Map;

@AllArgsConstructor
@RestController
@RequestMapping("/device")
@Tag(name = "设备管理")

public class DeviceController {
    private final DeviceService deviceService;
    private final RedisUtils redisUtils;


    @PostMapping("/bind/{deviceCode}")
    @Operation(summary = "绑定设备")
    @RequiresPermissions("sys:role:normal")
    public Result<DeviceEntity> bindDevice(@PathVariable String deviceCode) {
        UserDetail user = SecurityUser.getUser();

        String deviceHeaders = (String) redisUtils.get(RedisKeys.getDeviceCaptchaKey(deviceCode));
        if (StringUtils.isBlank(deviceHeaders)) {
            return new Result<DeviceEntity>().error(ErrorCode.DEVICE_CAPTCHA_ERROR);
        }
        DeviceHeaderDTO deviceHeader = JsonUtils.parseObject(deviceHeaders.getBytes(), DeviceHeaderDTO.class);
        DeviceEntity device = deviceService.bindDevice(user.getId(), deviceHeader);
        return new Result<DeviceEntity>().ok(device);
    }

    @GetMapping("/bind")
    @Operation(summary = "获取已绑定设备")
    @RequiresPermissions("sys:role:normal")
    public Result<List<DeviceEntity>> getUserDevices() {
        UserDetail user = SecurityUser.getUser();
        List<DeviceEntity> devices = deviceService.getUserDevices(user.getId());
        return new Result<List<DeviceEntity>>().ok(devices);
    }

    @PostMapping("/unbind")
    @Operation(summary = "解绑设备")
    @RequiresPermissions("sys:role:normal")
    public Result unbindDevice(@RequestBody DeviceUnBindDTO unDeviveBind) {
        UserDetail user = SecurityUser.getUser();
        deviceService.unbindDevice(user.getId(), unDeviveBind.getDeviceId());
        return new Result();
    }

    @GetMapping("/all")
    @Operation(summary = "设备列表（管理员）")
    @RequiresPermissions("sys:role:superAdmin")
    @Parameters({
            @Parameter(name = Constant.PAGE, description = "当前页码，从1开始", required = true),
            @Parameter(name = Constant.LIMIT, description = "每页显示记录数", required = true),
    })
    public Result<PageData<DeviceEntity>> adminDeviceList(
            @Parameter(hidden = true) @RequestParam Map<String, Object> params) {
        PageData<DeviceEntity> page = deviceService.adminDeviceList(params);
        return new Result<PageData<DeviceEntity>>().ok(page);
    }
}