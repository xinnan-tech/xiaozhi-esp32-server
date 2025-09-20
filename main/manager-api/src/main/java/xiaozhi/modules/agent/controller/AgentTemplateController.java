package xiaozhi.modules.agent.controller;

import java.util.List;
import java.util.Map;

import org.apache.shiro.authz.annotation.RequiresPermissions;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.Parameters;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.AllArgsConstructor;
import xiaozhi.common.constant.Constant;
import xiaozhi.common.page.PageData;
import xiaozhi.common.utils.ConvertUtils;
import xiaozhi.common.utils.Result;
import xiaozhi.common.utils.ResultUtils;
import xiaozhi.modules.agent.entity.AgentTemplateEntity;
import xiaozhi.modules.agent.service.AgentTemplateService;
import xiaozhi.modules.agent.vo.AgentTemplateVO;

@Tag(name = "智能体模板管理")
@AllArgsConstructor
@RestController
@RequestMapping("/agent/template")
public class AgentTemplateController {
    
    private final AgentTemplateService agentTemplateService;
    
    @GetMapping("/page")
    @Operation(summary = "获取模板分页列表")
    @RequiresPermissions("sys:role:superAdmin")
    @Parameters({
            @Parameter(name = Constant.PAGE, description = "当前页码，从1开始", required = true),
            @Parameter(name = Constant.LIMIT, description = "每页显示记录数", required = true),
            @Parameter(name = "agentName", description = "模板名称，模糊查询")
    })
    public Result<PageData<AgentTemplateVO>> getAgentTemplatesPage(
            @Parameter(hidden = true) @RequestParam Map<String, Object> params) {
        
        // 创建分页对象
        int page = Integer.parseInt(params.getOrDefault(Constant.PAGE, "1").toString());
        int limit = Integer.parseInt(params.getOrDefault(Constant.LIMIT, "10").toString());
        Page<AgentTemplateEntity> pageInfo = new Page<>(page, limit);
        
        // 创建查询条件
        QueryWrapper<AgentTemplateEntity> wrapper = new QueryWrapper<>();
        String agentName = (String) params.get("agentName");
        if (agentName != null && !agentName.isEmpty()) {
            wrapper.like("agent_name", agentName);
        }
        wrapper.orderByAsc("sort");
        
        // 执行分页查询
        IPage<AgentTemplateEntity> pageResult = agentTemplateService.page(pageInfo, wrapper);
        
        // 使用ConvertUtils转换为VO列表
        List<AgentTemplateVO> voList = ConvertUtils.sourceToTarget(pageResult.getRecords(), AgentTemplateVO.class);

        // 修复：使用构造函数创建PageData对象，而不是无参构造+setter
        PageData<AgentTemplateVO> pageData = new PageData<>(voList, pageResult.getTotal());

        return new Result<PageData<AgentTemplateVO>>().ok(pageData);
    }
    
    @GetMapping("/{id}")
    @Operation(summary = "获取模板详情")
    @RequiresPermissions("sys:role:superAdmin")
    public Result<AgentTemplateVO> getAgentTemplateById(@PathVariable("id") String id) {
        AgentTemplateEntity template = agentTemplateService.getById(id);
        if (template == null) {
            return ResultUtils.error("模板不存在");
        }
        
        // 使用ConvertUtils转换为VO
        AgentTemplateVO vo = ConvertUtils.sourceToTarget(template, AgentTemplateVO.class);
        
        return ResultUtils.success(vo);
    }
    
    @PostMapping
    @Operation(summary = "创建模板")
    @RequiresPermissions("sys:role:superAdmin")
    public Result<AgentTemplateEntity> createAgentTemplate(@Valid @RequestBody AgentTemplateEntity template) {
        // 设置排序值为下一个可用的序号
        template.setSort(agentTemplateService.getNextAvailableSort());
        
        boolean saved = agentTemplateService.save(template);
        if (saved) {
            return ResultUtils.success(template);
        } else {
            return ResultUtils.error("创建模板失败");
        }
    }
    
    @PutMapping
    @Operation(summary = "更新模板")
    @RequiresPermissions("sys:role:superAdmin")
    public Result<AgentTemplateEntity> updateAgentTemplate(@Valid @RequestBody AgentTemplateEntity template) {
        boolean updated = agentTemplateService.updateById(template);
        if (updated) {
            return ResultUtils.success(template);
        } else {
            return ResultUtils.error("更新模板失败");
        }
    }
    
    @DeleteMapping("/{id}")
    @Operation(summary = "删除模板")
    @RequiresPermissions("sys:role:superAdmin")
    public Result<String> deleteAgentTemplate(@PathVariable("id") String id) {
        // 先查询要删除的模板信息，获取其排序值
        AgentTemplateEntity template = agentTemplateService.getById(id);
        if (template == null) {
            return ResultUtils.error("模板不存在");
        }
        
        Integer deletedSort = template.getSort();
        
        // 执行删除操作
        boolean deleted = agentTemplateService.removeById(id);
        if (deleted) {
            // 删除成功后，重新排序剩余模板
            agentTemplateService.reorderTemplatesAfterDelete(deletedSort);
            return ResultUtils.success("删除模板成功");
        } else {
            return ResultUtils.error("删除模板失败");
        }
    }
    
    
    // 添加新的批量删除方法，使用不同的URL
    @PostMapping("/batch-remove")
    @Operation(summary = "批量删除模板")
    @RequiresPermissions("sys:role:superAdmin")
    public Result<String> batchRemoveAgentTemplates(@RequestBody List<String> ids) {
        boolean deleted = agentTemplateService.removeByIds(ids);
        if (deleted) {
            return ResultUtils.success("批量删除成功");
        } else {
            return ResultUtils.error("批量删除模板失败");
        }
    }
}