package xiaozhi.modules.model.controller;

import java.util.List;

import org.apache.shiro.authz.annotation.RequiresPermissions;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.AllArgsConstructor;
import xiaozhi.common.page.PageData;
import xiaozhi.common.utils.Result;
import xiaozhi.common.validator.group.UpdateGroup;
import xiaozhi.modules.model.dto.ModelProviderDTO;
import xiaozhi.modules.model.service.ModelProviderService;

@AllArgsConstructor
@RestController
@RequestMapping("/models/provider")
@Tag(name = "模型供应器")
public class ModelProviderController {

    private final ModelProviderService modelProviderService;

    @GetMapping
    @Operation(summary = "获取模型供应器列表")
    @RequiresPermissions("sys:role:superAdmin")
    public Result<PageData<ModelProviderDTO>> getListPage(ModelProviderDTO modelProviderDTO,
            @RequestParam(required = true, defaultValue = "0") String page,
            @RequestParam(required = true, defaultValue = "10") String limit) {
        return new Result<PageData<ModelProviderDTO>>()
                .ok(modelProviderService.getListPage(modelProviderDTO, page, limit));
    }

    @PostMapping
    @Operation(summary = "新增模型供应器")
    @RequiresPermissions("sys:role:superAdmin")
    public Result<ModelProviderDTO> add(@RequestBody @Validated ModelProviderDTO modelProviderDTO) {
        ModelProviderDTO resp = modelProviderService.add(modelProviderDTO);
        return new Result<ModelProviderDTO>().ok(resp);
    }

    @PutMapping
    @Operation(summary = "修改模型供应器")
    @RequiresPermissions("sys:role:superAdmin")
    public Result<ModelProviderDTO> edit(@RequestBody @Validated(UpdateGroup.class) ModelProviderDTO modelProviderDTO) {
        ModelProviderDTO resp = modelProviderService.edit(modelProviderDTO);
        return new Result<ModelProviderDTO>().ok(resp);
    }

    @PostMapping("/delete")
    @Operation(summary = "删除模型供应器")
    @RequiresPermissions("sys:role:superAdmin")
    @Parameter(name = "ids", description = "ID数组", required = true)
    public Result<Void> delete(@RequestBody List<String> ids) {
        modelProviderService.delete(ids);
        return new Result<>();
    }

}
