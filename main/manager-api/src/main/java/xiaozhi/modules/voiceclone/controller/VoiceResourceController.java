package xiaozhi.modules.voiceclone.controller;

import java.util.List;
import java.util.Map;

import org.apache.shiro.authz.annotation.RequiresPermissions;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.Parameters;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import xiaozhi.common.constant.Constant;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.page.PageData;
import xiaozhi.common.utils.Result;
import xiaozhi.common.validator.ValidatorUtils;
import xiaozhi.modules.model.service.ModelConfigService;
import xiaozhi.modules.voiceclone.dto.VoiceCloneDTO;
import xiaozhi.modules.voiceclone.dto.VoiceCloneResponseDTO;
import xiaozhi.modules.voiceclone.service.VoiceCloneService;

@Tag(name = "音色资源管理", description = "音色资源开通相关接口")
@Slf4j
@RestController
@RequiredArgsConstructor
@RequestMapping("/voiceResource")
public class VoiceResourceController {

    private final VoiceCloneService voiceCloneService;
    private final ModelConfigService modelConfigService;

    @GetMapping
    @Operation(summary = "分页查询音色资源")
    @Parameters({
            @Parameter(name = Constant.PAGE, description = "当前页码，从1开始", required = true),
            @Parameter(name = Constant.LIMIT, description = "每页显示记录数", required = true)
    })
    @RequiresPermissions("sys:role:superAdmin")
    public Result<PageData<VoiceCloneResponseDTO>> page(
            @Parameter(hidden = true) @RequestParam Map<String, Object> params) {
        ValidatorUtils.validateEntity(params);
        PageData<VoiceCloneResponseDTO> page = voiceCloneService.pageWithNames(params);
        return new Result<PageData<VoiceCloneResponseDTO>>().ok(page);
    }

    @GetMapping("{id}")
    @Operation(summary = "获取音色资源详情")
    @RequiresPermissions("sys:role:superAdmin")
    public Result<VoiceCloneResponseDTO> get(@PathVariable("id") String id) {
        VoiceCloneResponseDTO data = voiceCloneService.getByIdWithNames(id);
        return new Result<VoiceCloneResponseDTO>().ok(data);
    }

    @PostMapping
    @Operation(summary = "新增音色资源")
    @RequiresPermissions("sys:role:superAdmin")
    public Result<Void> save(@RequestBody VoiceCloneDTO dto) {
        if (dto == null) {
            return new Result<Void>().error(ErrorCode.VOICE_RESOURCE_INFO_EMPTY);
        }
        if (dto.getModelId() == null || dto.getModelId().isEmpty()) {
            return new Result<Void>().error(ErrorCode.VOICE_RESOURCE_PLATFORM_NAME_EMPTY);
        }
        if (dto.getVoiceIds() == null || dto.getVoiceIds().isEmpty()) {
            return new Result<Void>().error(ErrorCode.VOICE_RESOURCE_ID_EMPTY);
        }
        if (dto.getUserId() == null) {
            return new Result<Void>().error(ErrorCode.VOICE_RESOURCE_ACCOUNT_EMPTY);
        }
        try {
            voiceCloneService.save(dto);
            return new Result<Void>();
        } catch (xiaozhi.common.exception.RenException e) {
            return new Result<Void>().error(e.getCode(), e.getMsg());
        } catch (RuntimeException e) {
            return new Result<Void>().error(ErrorCode.ADD_DATA_FAILED, e.getMessage());
        }
    }

    @DeleteMapping("/{id}")
    @Operation(summary = "删除音色资源")
    @RequiresPermissions("sys:role:superAdmin")
    public Result<Void> delete(@PathVariable("id") String[] ids) {
        if (ids == null || ids.length == 0) {
            return new Result<Void>().error(ErrorCode.VOICE_RESOURCE_DELETE_ID_EMPTY);
        }
        voiceCloneService.delete(ids);
        return new Result<Void>();
    }

    @GetMapping("/user/{userId}")
    @Operation(summary = "根据用户ID获取音色资源列表")
    @RequiresPermissions("sys:role:normal")
    public Result<List<VoiceCloneResponseDTO>> getByUserId(@PathVariable("userId") Long userId) {
        List<VoiceCloneResponseDTO> list = voiceCloneService.getByUserIdWithNames(userId);
        return new Result<List<VoiceCloneResponseDTO>>().ok(list);
    }

    @GetMapping("/ttsPlatforms")
    @Operation(summary = "获取TTS平台列表")
    @RequiresPermissions("sys:role:superAdmin")
    public Result<List<Map<String, Object>>> getTtsPlatformList() {
        List<Map<String, Object>> list = modelConfigService.getTtsPlatformList();
        return new Result<List<Map<String, Object>>>().ok(list);
    }
}
