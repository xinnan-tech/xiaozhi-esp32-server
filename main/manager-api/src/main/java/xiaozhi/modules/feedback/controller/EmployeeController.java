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
import xiaozhi.modules.feedback.dto.EmployeeDTO;
import xiaozhi.modules.feedback.service.EmployeeService;
import xiaozhi.modules.feedback.vo.EmployeeVO;

@AllArgsConstructor
@RestController
@RequestMapping("/feedback/employee")
@Tag(name = "员工管理")
public class EmployeeController {

    private final EmployeeService employeeService;

    @GetMapping("/list")
    @Operation(summary = "员工分页列表")
    @RequiresPermissions("sys:role:superAdmin")
    public Result<PageData<EmployeeVO>> page(@Parameter(hidden = true) @RequestParam Map<String, Object> params) {
        String storeId = (String) params.get("storeId");
        String name = (String) params.get("name");
        String page = (String) params.get(Constant.PAGE);
        String limit = (String) params.get(Constant.LIMIT);
        PageData<EmployeeVO> data = employeeService.page(storeId, name, page, limit);
        return new Result<PageData<EmployeeVO>>().ok(data);
    }

    @PostMapping
    @Operation(summary = "新增员工")
    @RequiresPermissions("sys:role:superAdmin")
    public Result<Void> save(@RequestBody EmployeeDTO dto) {
        ValidatorUtils.validateEntity(dto);
        employeeService.save(dto);
        return new Result<>();
    }

    @PutMapping("/{id}")
    @Operation(summary = "修改员工")
    @RequiresPermissions("sys:role:superAdmin")
    public Result<Void> update(@PathVariable String id, @RequestBody EmployeeDTO dto) {
        employeeService.update(id, dto);
        return new Result<>();
    }

    @PostMapping("/delete")
    @Operation(summary = "删除员工")
    @RequiresPermissions("sys:role:superAdmin")
    public Result<Void> delete(@RequestBody String[] ids) {
        employeeService.delete(ids);
        return new Result<>();
    }
}
