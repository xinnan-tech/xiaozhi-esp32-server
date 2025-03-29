package xiaozhi.modules.model.controller;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.AllArgsConstructor;
import org.apache.shiro.authz.annotation.RequiresPermissions;
import org.springframework.web.bind.annotation.*;
import xiaozhi.common.page.PageData;
import xiaozhi.common.utils.Result;
import xiaozhi.modules.model.dto.ModelConfigBodyDTO;
import xiaozhi.modules.model.dto.ModelConfigDTO;
import xiaozhi.modules.model.dto.ModelProviderDTO;
import xiaozhi.modules.model.service.ModelConfigService;
import xiaozhi.modules.model.service.ModelProviderService;

import java.util.List;

@AllArgsConstructor
@RestController
@RequestMapping("/models")
@Tag(name = "模型配置")
public class ModelController {

    private final ModelProviderService modelProviderService;

    private final ModelConfigService modelConfigService;

    @GetMapping("/models/names")
    @Operation(summary = "获取所有模型名称")
    @RequiresPermissions("sys:role:superAdmin")
    public Result<List<String>> getModelNames(@RequestParam String modelType,
                                              @RequestParam(required = false) String modelName) {
        List<String> modelNameList = modelConfigService.getModelCodeList(modelType, modelName);
        return new Result<List<String>>().ok(modelNameList);
    }

    @GetMapping("/{modelType}/provideTypes")
    @Operation(summary = "获取模型供应器列表")
    @RequiresPermissions("sys:role:superAdmin")
    public Result<List<ModelProviderDTO>> getModelProviderList(@PathVariable String modelType) {
        List<ModelProviderDTO> modelProviderDTOS = modelProviderService.getListByModelType(modelType);
        return new Result<List<ModelProviderDTO>>().ok(modelProviderDTOS);
    }

    @GetMapping("/{modelType}/{provideCode}/fields")
    @Operation(summary = "获取模型供应器字段")
    @RequiresPermissions("sys:role:superAdmin")
    public Result<List<String>> getModelProviderFields(@PathVariable String modelType, @PathVariable String provideCode) {
        List<String> fieldList = modelProviderService.getFieldList(modelType, provideCode);
        return new Result<List<String>>().ok(fieldList);
    }


    @GetMapping("/models/list")
    @Operation(summary = "获取模型配置列表")
    @RequiresPermissions("sys:role:superAdmin")
    public Result<PageData<ModelConfigDTO>> getModelConfigList(@RequestParam String modelType,
                                                               @RequestParam(required = false) String modelName,
                                                               @RequestParam(required = false, defaultValue = "0") Integer page,
                                                               @RequestParam(required = false,defaultValue = "10") Integer limit) {
        PageData<ModelConfigDTO> pageList = modelConfigService.getPageList(modelType, modelName, page, limit);
        return new Result<PageData<ModelConfigDTO>>().ok(pageList);
    }


    @PostMapping("/models/{modelType}/{provideCode}")
    @Operation(summary = "新增模型配置")
    @RequiresPermissions("sys:role:superAdmin")
    public Result<ModelConfigDTO> addModelConfig(@PathVariable String modelType,
                                                 @PathVariable String provideCode,
                                                 @RequestBody ModelConfigBodyDTO modelConfigBodyDTO) {
        ModelConfigDTO modelConfigDTO = modelConfigService.add(modelType, provideCode, modelConfigBodyDTO);
        return new Result<ModelConfigDTO>().ok(modelConfigDTO);
    }


    @PutMapping("/models/{modelType}/{provideCode}/{id}")
    @Operation(summary = "编辑模型配置")
    @RequiresPermissions("sys:role:superAdmin")
    public Result<ModelConfigDTO> editModelConfig(@PathVariable String modelType,
                                                  @PathVariable String provideCode,
                                                  @PathVariable String id,
                                                  @RequestBody ModelConfigBodyDTO modelConfigBodyDTO) {
        ModelConfigDTO modelConfigDTO = modelConfigService.edit(modelType, provideCode, id, modelConfigBodyDTO);
        return new Result<ModelConfigDTO>().ok(modelConfigDTO);
    }


    @DeleteMapping("/models/{modelType}/{provideCode}/{id}")
    @Operation(summary = "删除模型配置")
    @RequiresPermissions("sys:role:superAdmin")
    public Result<Void> deleteModelConfig(@PathVariable String modelType, @PathVariable String provideCode, @PathVariable String id) {
        modelConfigService.delete(modelType, provideCode, id);
        return new Result<>();
    }

    @GetMapping("/models/{modelName}/voices")
    @Operation(summary = "获取模型音色")
    @RequiresPermissions("sys:role:normal")
    public Result<List<String>> getVoiceList(@PathVariable String modelName,
                                             @RequestParam(required = false) String voiceName) {

        List<String> voiceList = modelConfigService.getVoiceList(modelName, voiceName);
        return new Result<List<String>>().ok(voiceList);
    }
}
