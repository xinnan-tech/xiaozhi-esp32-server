package xiaozhi.modules.device.controller;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.apache.shiro.authz.annotation.RequiresPermissions;
import org.springframework.web.bind.annotation.*;
import xiaozhi.common.utils.Result;
import xiaozhi.modules.device.entity.DeviceCommandEntity;
import xiaozhi.modules.device.service.DeviceCommandService;

import java.util.List;

@Tag(name = "设备指令管理")
@RestController
@RequiredArgsConstructor
@RequestMapping("/device/command")
public class DeviceCommandController {
    private final DeviceCommandService deviceCommandService;

    @PostMapping("/add")
    @Operation(summary = "添加设备指令")
    // @RequiresPermissions("sys:role:superAdmin")
    public Result<Void> addCommand(@RequestBody DeviceCommandEntity entity) {
        deviceCommandService.addCommand(entity);
        return new Result<>();
    }

    @GetMapping("/list/{deviceId}")
    @Operation(summary = "查询设备指令列表")
    // @RequiresPermissions("sys:role:superAdmin")
    public Result<List<DeviceCommandEntity>> getCommands(@PathVariable String deviceId) {
        List<DeviceCommandEntity> list = deviceCommandService.getCommandsByDeviceId(deviceId);
        return new Result<List<DeviceCommandEntity>>().ok(list);
    }

    @PutMapping("/executed/{id}")
    @Operation(summary = "设置指令为已执行")
    // @RequiresPermissions("sys:role:superAdmin")
    public Result<Void> setCommandExecuted(@PathVariable String id) {
        deviceCommandService.setCommandExecuted(id);
        return new Result<>();
    }

    @GetMapping("/{id}")
    @Operation(summary = "根据ID查询指令详情")
    // @RequiresPermissions("sys:role:superAdmin")
    public Result<DeviceCommandEntity> getById(@PathVariable String id) {
        DeviceCommandEntity entity = deviceCommandService.getById(id);
        return new Result<DeviceCommandEntity>().ok(entity);
    }

    /*
     * @Operation(summary = "消费一个设备指令")
     */
    @PostMapping("/consume")
    @Operation(summary = "消费一个设备指令")
    // @RequiresPermissions("sys:role:superAdmin")
    public Result<DeviceCommandEntity> consumeCommand(@RequestBody ConsumeCommandRequest request) {
        DeviceCommandEntity entity = deviceCommandService.consumeCommand(request.getDeviceId());
        if (entity == null) {
            return new Result<DeviceCommandEntity>().error("没有可消费的指令");
        }
        return new Result<DeviceCommandEntity>().ok(entity);
    }

    // 新增请求体类
    static class ConsumeCommandRequest {
        private String deviceId;

        public String getDeviceId() {
            return deviceId;
        }

        public void setDeviceId(String deviceId) {
            this.deviceId = deviceId;
        }
    }
}
