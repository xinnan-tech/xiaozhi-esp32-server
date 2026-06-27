package xiaozhi.modules.device.controller;

import java.util.Map;

import org.apache.commons.lang3.StringUtils;
import org.apache.shiro.authz.annotation.RequiresPermissions;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.AllArgsConstructor;
import xiaozhi.common.user.UserDetail;
import xiaozhi.common.utils.Result;
import xiaozhi.common.validator.ValidatorUtils;
import xiaozhi.modules.device.dto.DeviceAttributeBatchDTO;
import xiaozhi.modules.device.dto.DeviceAttributeDTO;
import xiaozhi.modules.device.entity.DeviceEntity;
import xiaozhi.modules.device.service.DeviceAttributeService;
import xiaozhi.modules.device.service.DeviceService;
import xiaozhi.modules.security.user.SecurityUser;

@Tag(name = "设备属性管理")
@RestController
@RequestMapping("/device/attribute")
@AllArgsConstructor
public class DeviceAttributeController {

    private final DeviceAttributeService deviceAttributeService;
    private final DeviceService deviceService;

    @GetMapping("/{deviceId}")
    @Operation(summary = "获取设备所有属性")
    @RequiresPermissions("sys:role:normal")
    public Result<Map<String, String>> list(@PathVariable String deviceId) {
        DeviceEntity device = deviceService.getDeviceByMacAddress(deviceId);
        if (device == null || !device.getUserId().equals(SecurityUser.getUser().getId())) {
            return new Result<Map<String, String>>().error("设备不存在");
        }
        return new Result<Map<String, String>>().ok(deviceAttributeService.getAttributesByDeviceId(deviceId));
    }

    @GetMapping("/{deviceId}/{attrKey}")
    @Operation(summary = "获取单个设备属性")
    @RequiresPermissions("sys:role:normal")
    public Result<String> get(@PathVariable String deviceId, @PathVariable String attrKey) {
        DeviceEntity device = deviceService.getDeviceByMacAddress(deviceId);
        if (device == null || !device.getUserId().equals(SecurityUser.getUser().getId())) {
            return new Result<String>().error("设备不存在");
        }
        return new Result<String>().ok(deviceAttributeService.getAttributeValue(deviceId, attrKey));
    }

    @PutMapping("/{deviceId}/{attrKey}")
    @Operation(summary = "更新设备属性")
    @RequiresPermissions("sys:role:normal")
    public Result<Void> update(@PathVariable String deviceId, @PathVariable String attrKey,
            @RequestBody(required = false) String attrValue) {
        DeviceEntity device = deviceService.getDeviceByMacAddress(deviceId);
        if (device == null || !device.getUserId().equals(SecurityUser.getUser().getId())) {
            return new Result<Void>().error("设备不存在");
        }
        deviceAttributeService.saveOrUpdateAttribute(deviceId, attrKey, attrValue);
        return new Result<Void>();
    }

    @PostMapping("/batch")
    @Operation(summary = "批量更新设备属性")
    @RequiresPermissions("sys:role:normal")
    public Result<Void> batchUpdate(@Valid @RequestBody DeviceAttributeBatchDTO dto) {
        ValidatorUtils.validateEntity(dto);
        DeviceEntity device = deviceService.getDeviceByMacAddress(dto.getDeviceId());
        if (device == null || !device.getUserId().equals(SecurityUser.getUser().getId())) {
            return new Result<Void>().error("设备不存在");
        }
        deviceAttributeService.saveOrUpdateAttributes(dto.getDeviceId(), dto.getAttributes());
        return new Result<Void>();
    }

    @DeleteMapping("/{deviceId}/{attrKey}")
    @Operation(summary = "删除设备属性")
    @RequiresPermissions("sys:role:normal")
    public Result<Void> delete(@PathVariable String deviceId, @PathVariable String attrKey) {
        DeviceEntity device = deviceService.getDeviceByMacAddress(deviceId);
        if (device == null || !device.getUserId().equals(SecurityUser.getUser().getId())) {
            return new Result<Void>().error("设备不存在");
        }
        deviceAttributeService.deleteAttribute(deviceId, attrKey);
        return new Result<Void>();
    }
}
