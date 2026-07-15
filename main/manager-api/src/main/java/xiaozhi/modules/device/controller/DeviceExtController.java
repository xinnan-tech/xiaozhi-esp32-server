package xiaozhi.modules.device.controller;

import java.util.Map;

import org.apache.shiro.authz.annotation.RequiresPermissions;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import cn.hutool.json.JSONUtil;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.AllArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import xiaozhi.common.utils.Result;
import xiaozhi.modules.agent.service.PersonaMatcherService;
import xiaozhi.modules.device.entity.DeviceEntity;
import xiaozhi.modules.device.entity.DeviceExtEntity;
import xiaozhi.modules.device.service.DeviceExtService;
import xiaozhi.modules.device.service.DeviceService;
import xiaozhi.modules.security.user.SecurityUser;

@Slf4j
@Tag(name = "设备扩展字段")
@RestController
@RequestMapping("/device")
@AllArgsConstructor
public class DeviceExtController {

    private final DeviceExtService deviceExtService;
    private final DeviceService deviceService;
    private final PersonaMatcherService personaMatcherService;

    /** 校验设备存在且归属当前用户;越权时返回 null(调用方据此返回错误) */
    private DeviceEntity assertOwner(String id) {
        DeviceEntity device = deviceService.selectById(id);
        Long curUid = SecurityUser.getUserId();
        if (device == null || device.getUserId() == null || !device.getUserId().equals(curUid)) {
            return null;
        }
        return device;
    }

    @GetMapping("/{id}/ext")
    @Operation(summary = "取设备扩展字段(JSON 对象:孩子信息+家长期望)")
    @RequiresPermissions("sys:role:normal")
    public Result<Object> getExt(@PathVariable String id) {
        if (assertOwner(id) == null) {
            return new Result<>().error("设备不存在");
        }
        DeviceExtEntity e = deviceExtService.getByDeviceId(id);
        Object obj = (e != null && e.getExtJson() != null && !e.getExtJson().isBlank())
                ? JSONUtil.parseObj(e.getExtJson())
                : JSONUtil.parseObj("{}");
        return new Result<>().ok(obj);
    }

    @PutMapping("/{id}/ext")
    @Operation(summary = "整体覆盖设备扩展字段(body=JSON 对象)。保存后异步触发冷启动匹配(若该设备无 manual 锁定)")
    @RequiresPermissions("sys:role:normal")
    public Result<Void> saveExt(@PathVariable String id, @RequestBody Map<String, Object> body) {
        if (assertOwner(id) == null) {
            return new Result<Void>().error("设备不存在");
        }
        deviceExtService.saveOrUpdate(id, JSONUtil.toJsonStr(body));
        // 异步触发冷启动匹配(@Async 在 PersonaMatcherService 内生效,不阻塞本次请求)
        try {
            personaMatcherService.matchColdStart(id);
        } catch (Exception e) {
            log.warn("[device-ext] 触发冷启动匹配失败 device={}:{}", id, e.getMessage());
        }
        return new Result<>();
    }
}
