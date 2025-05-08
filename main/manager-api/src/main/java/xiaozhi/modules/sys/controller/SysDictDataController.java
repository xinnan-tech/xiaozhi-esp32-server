package xiaozhi.modules.sys.controller;

import java.util.List;
import java.util.Map;

import org.apache.commons.lang3.StringUtils;
import org.apache.shiro.authz.annotation.RequiresPermissions;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.Parameters;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.AllArgsConstructor;
import xiaozhi.common.constant.Constant;
import xiaozhi.common.page.PageData;
import xiaozhi.common.utils.Result;
import xiaozhi.common.validator.ValidatorUtils;
import xiaozhi.modules.sys.dto.SysDictDataDTO;
import xiaozhi.modules.sys.service.SysDictDataService;
import xiaozhi.modules.sys.vo.SysDictDataItem;
import xiaozhi.modules.sys.vo.SysDictDataVO;

/**
 * 字典数据管理
 *
 * @author czc
 * @since 2025-04-30
 */
@AllArgsConstructor
@RestController
@RequestMapping("/admin/dict/data")
@Tag(name = "字典数据管理")
public class SysDictDataController {
    private final SysDictDataService sysDictDataService;

    @GetMapping("/page")
    @Operation(summary = "分页查询字典数据")
    @RequiresPermissions("sys:role:superAdmin")
    @Parameters({ @Parameter(name = "dictTypeId", description = "字典类型ID", required = true),
            @Parameter(name = "dictLabel", description = "数据标签"), @Parameter(name = "dictValue", description = "数据值"),
            @Parameter(name = Constant.PAGE, description = "当前页码，从1开始", required = true),
            @Parameter(name = Constant.LIMIT, description = "每页显示记录数", required = true) })
    public Result<PageData<SysDictDataVO>> page(@Parameter(hidden = true) @RequestParam Map<String, Object> params) {
        ValidatorUtils.validateEntity(params);
        // 强制校验dictTypeId是否存在
        if (!params.containsKey("dictTypeId") || StringUtils.isEmpty(String.valueOf(params.get("dictTypeId")))) {
            return new Result<PageData<SysDictDataVO>>().error("dictTypeId不能为空");
        }

        PageData<SysDictDataVO> page = sysDictDataService.page(params);
        return new Result<PageData<SysDictDataVO>>().ok(page);
    }

    @GetMapping("/{id}")
    @Operation(summary = "获取字典数据详情")
    @RequiresPermissions("sys:role:superAdmin")
    public Result<SysDictDataVO> get(@PathVariable("id") Long id) {
        SysDictDataVO vo = sysDictDataService.get(id);
        return new Result<SysDictDataVO>().ok(vo);
    }

    @PostMapping("/save")
    @Operation(summary = "新增字典数据")
    @RequiresPermissions("sys:role:superAdmin")
    public Result<Void> save(@RequestBody SysDictDataDTO dto) {
        ValidatorUtils.validateEntity(dto);
        sysDictDataService.save(dto);
        return new Result<>();
    }

    @PutMapping("/update")
    @Operation(summary = "修改字典数据")
    @RequiresPermissions("sys:role:superAdmin")
    public Result<Void> update(@RequestBody SysDictDataDTO dto) {
        ValidatorUtils.validateEntity(dto);
        sysDictDataService.update(dto);
        return new Result<>();
    }

    @PostMapping("/delete")
    @Operation(summary = "删除字典数据")
    @RequiresPermissions("sys:role:superAdmin")
    @Parameter(name = "ids", description = "ID数组", required = true)
    public Result<Void> delete(@RequestBody Long[] ids) {
        sysDictDataService.delete(ids);
        return new Result<>();
    }

    @GetMapping("/type/{dictType}")
    @Operation(summary = "获取字典数据列表")
    @RequiresPermissions("sys:role:normal")
    public Result<List<SysDictDataItem>> getDictDataByType(@PathVariable("dictType") String dictType) {
        List<SysDictDataItem> list = sysDictDataService.getDictDataByType(dictType);
        return new Result<List<SysDictDataItem>>().ok(list);
    }

}
