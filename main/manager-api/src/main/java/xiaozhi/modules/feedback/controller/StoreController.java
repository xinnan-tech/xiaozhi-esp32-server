package xiaozhi.modules.feedback.controller;

import java.util.Map;

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
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.AllArgsConstructor;
import xiaozhi.common.constant.Constant;
import xiaozhi.common.page.PageData;
import xiaozhi.common.utils.Result;
import xiaozhi.common.validator.ValidatorUtils;
import xiaozhi.modules.feedback.dto.StoreDTO;
import xiaozhi.modules.feedback.service.StoreService;
import xiaozhi.modules.feedback.vo.StoreVO;

@AllArgsConstructor
@RestController
@RequestMapping("/feedback/store")
@Tag(name = "门店管理")
public class StoreController {

    private final StoreService storeService;

    @GetMapping("/list")
    @Operation(summary = "门店分页列表")
    @RequiresPermissions("sys:role:superAdmin")
    public Result<PageData<StoreVO>> page(@Parameter(hidden = true) @RequestParam Map<String, Object> params) {
        String storeName = (String) params.get("storeName");
        String page = (String) params.get(Constant.PAGE);
        String limit = (String) params.get(Constant.LIMIT);
        PageData<StoreVO> data = storeService.page(storeName, page, limit);
        return new Result<PageData<StoreVO>>().ok(data);
    }

    @PostMapping
    @Operation(summary = "新增门店")
    @RequiresPermissions("sys:role:superAdmin")
    public Result<Void> save(@RequestBody StoreDTO dto) {
        storeService.save(dto);
        return new Result<>();
    }

    @PutMapping("/{id}")
    @Operation(summary = "修改门店")
    @RequiresPermissions("sys:role:superAdmin")
    public Result<Void> update(@PathVariable String id, @RequestBody StoreDTO dto) {
        storeService.update(id, dto);
        return new Result<>();
    }

    @PostMapping("/delete")
    @Operation(summary = "删除门店")
    @RequiresPermissions("sys:role:superAdmin")
    public Result<Void> delete(@RequestBody String[] ids) {
        storeService.delete(ids);
        return new Result<>();
    }
}
