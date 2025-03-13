package xiaozhi.modules.device.controller;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.AllArgsConstructor;
import org.apache.shiro.authz.annotation.RequiresPermissions;
import org.springframework.web.bind.annotation.*;
import xiaozhi.common.page.PageData;
import xiaozhi.common.user.UserDetail;
import xiaozhi.common.utils.Result;
import xiaozhi.modules.device.dto.DeviceDTO;
import xiaozhi.modules.device.service.DeviceService;
import xiaozhi.modules.security.user.SecurityUser;
import java.util.List;
import java.util.Map;
import xiaozhi.common.validator.AssertUtils;

@AllArgsConstructor
@RestController
@RequestMapping("/device")
@Tag(name = "设备管理")

public class DeviceController {
    private final DeviceService deviceService;

    @PostMapping("/bind")
    @Operation(summary = "绑定设备")
    @RequiresPermissions("sys:device:bind")
    public Result<DeviceDTO> register(@RequestBody String deviceCode) {
        UserDetail user = SecurityUser.getUser();

        AssertUtils.isBlank(deviceCode, 400, "设备编码不能为空");
        DeviceDTO device = deviceService.bindDevice(user.getId(), deviceCode);
        return new Result<DeviceDTO>().ok(device);
    }

    @GetMapping("/bind")
    @Operation(summary = "获取已绑定设备")
    @RequiresPermissions("sys:device:bind")
    public Result<List<DeviceDTO>> getUserDevices() {
        UserDetail user = SecurityUser.getUser();
        List<DeviceDTO> devices = deviceService.getUserDevices(user.getId());
        return new Result<List<DeviceDTO>>().ok(devices);
    }

    @PutMapping("/unbind")
    @Operation(summary = "解绑设备")
    @RequiresPermissions("sys:device:unbind")
    public Result unbindDevice(@RequestBody Long deviceId) {
        UserDetail user = SecurityUser.getUser();
        deviceService.unbindDevice(user.getId(), deviceId);
        return new Result();
    }

    @GetMapping("/all")
    @Operation(summary = "设备列表（管理员）")
    @RequiresPermissions("sys:device:all")
    public Result<PageData<DeviceDTO>> adminDeviceList(
            @Parameter(hidden = true) @RequestParam Map<String, Object> params) {
        PageData<DeviceDTO> page = deviceService.adminDeviceList(params);
        return new Result<PageData<DeviceDTO>>().ok(page);
    }
}