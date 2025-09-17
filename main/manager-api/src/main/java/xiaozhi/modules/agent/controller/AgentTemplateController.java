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
    
    @GetMapping("/all")
    @Operation(summary = "获取所有模板列表")
    @RequiresPermissions("sys:role:normal")
    public Result<List<AgentTemplateVO>> getAgentTemplates() {
        List<AgentTemplateEntity> templates = agentTemplateService.list();
        // 转换为VO列表
        List<AgentTemplateVO> voList = templates.stream().map(template -> {
            AgentTemplateVO vo = new AgentTemplateVO();
            // 复制属性
            vo.setId(template.getId());
            vo.setAgentCode(template.getAgentCode());
            vo.setAgentName(template.getAgentName());
            vo.setAsrModelId(template.getAsrModelId());
            vo.setVadModelId(template.getVadModelId());
            vo.setLlmModelId(template.getLlmModelId());
            vo.setVllmModelId(template.getVllmModelId());
            vo.setTtsModelId(template.getTtsModelId());
            vo.setTtsVoiceId(template.getTtsVoiceId());
            vo.setMemModelId(template.getMemModelId());
            vo.setIntentModelId(template.getIntentModelId());
            vo.setChatHistoryConf(template.getChatHistoryConf());
            vo.setSystemPrompt(template.getSystemPrompt());
            vo.setSummaryMemory(template.getSummaryMemory());
            vo.setLangCode(template.getLangCode());
            vo.setLanguage(template.getLanguage());
            vo.setSort(template.getSort());
            vo.setCreator(template.getCreator());
            vo.setCreatedAt(template.getCreatedAt());
            vo.setUpdater(template.getUpdater());
            vo.setUpdatedAt(template.getUpdatedAt());
            return vo;
        }).toList();
        return new Result<List<AgentTemplateVO>>().ok(voList);
    }
    
    @GetMapping("/page")
    @Operation(summary = "获取模板分页列表")
    @RequiresPermissions("sys:role:normal")
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
        
        // 转换为PageData对象
        List<AgentTemplateVO> voList = pageResult.getRecords().stream().map(template -> {
            AgentTemplateVO vo = new AgentTemplateVO();
            // 复制属性
            vo.setId(template.getId());
            vo.setAgentCode(template.getAgentCode());
            vo.setAgentName(template.getAgentName());
            vo.setAsrModelId(template.getAsrModelId());
            vo.setVadModelId(template.getVadModelId());
            vo.setLlmModelId(template.getLlmModelId());
            vo.setVllmModelId(template.getVllmModelId());
            vo.setTtsModelId(template.getTtsModelId());
            vo.setTtsVoiceId(template.getTtsVoiceId());
            vo.setMemModelId(template.getMemModelId());
            vo.setIntentModelId(template.getIntentModelId());
            vo.setChatHistoryConf(template.getChatHistoryConf());
            vo.setSystemPrompt(template.getSystemPrompt());
            vo.setSummaryMemory(template.getSummaryMemory());
            vo.setLangCode(template.getLangCode());
            vo.setLanguage(template.getLanguage());
            vo.setSort(template.getSort());
            vo.setCreator(template.getCreator());
            vo.setCreatedAt(template.getCreatedAt());
            vo.setUpdater(template.getUpdater());
            vo.setUpdatedAt(template.getUpdatedAt());
            return vo;
        }).toList();

        // 修复：使用构造函数创建PageData对象，而不是无参构造+setter
        PageData<AgentTemplateVO> pageData = new PageData<>(voList, pageResult.getTotal());

        return new Result<PageData<AgentTemplateVO>>().ok(pageData);
    }
    
    @GetMapping("/{id}")
    @Operation(summary = "获取模板详情")
    @RequiresPermissions("sys:role:normal")
    public Result<AgentTemplateVO> getAgentTemplateById(@PathVariable("id") String id) {
        AgentTemplateEntity template = agentTemplateService.getById(id);
        if (template == null) {
            return ResultUtils.error("模板不存在");
        }
        
        // 转换为VO
        AgentTemplateVO vo = new AgentTemplateVO();
        // 复制属性
        vo.setId(template.getId());
        vo.setAgentCode(template.getAgentCode());
        vo.setAgentName(template.getAgentName());
        vo.setAsrModelId(template.getAsrModelId());
        vo.setVadModelId(template.getVadModelId());
        vo.setLlmModelId(template.getLlmModelId());
        vo.setVllmModelId(template.getVllmModelId());
        vo.setTtsModelId(template.getTtsModelId());
        vo.setTtsVoiceId(template.getTtsVoiceId());
        vo.setMemModelId(template.getMemModelId());
        vo.setIntentModelId(template.getIntentModelId());
        vo.setChatHistoryConf(template.getChatHistoryConf());
        vo.setSystemPrompt(template.getSystemPrompt());
        vo.setSummaryMemory(template.getSummaryMemory());
        vo.setLangCode(template.getLangCode());
        vo.setLanguage(template.getLanguage());
        vo.setSort(template.getSort());
        vo.setCreator(template.getCreator());
        vo.setCreatedAt(template.getCreatedAt());
        vo.setUpdater(template.getUpdater());
        vo.setUpdatedAt(template.getUpdatedAt());
        
        return ResultUtils.success(vo);
    }
    
    @PostMapping
    @Operation(summary = "创建模板")
    @RequiresPermissions("sys:role:normal")
    public Result<AgentTemplateEntity> createAgentTemplate(@Valid @RequestBody AgentTemplateEntity template) {
        boolean saved = agentTemplateService.save(template);
        if (saved) {
            return ResultUtils.success(template);
        } else {
            return ResultUtils.error("创建模板失败");
        }
    }
    
    @PutMapping
    @Operation(summary = "更新模板")
    @RequiresPermissions("sys:role:normal")
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
    @RequiresPermissions("sys:role:normal")
    public Result<String> deleteAgentTemplate(@PathVariable("id") String id) {
        boolean deleted = agentTemplateService.removeById(id);
        if (deleted) {
            return ResultUtils.success("删除成功");
        } else {
            return ResultUtils.error("删除模板失败");
        }
    }
    
    @DeleteMapping("/batch-delete")
    @Operation(summary = "批量删除模板")
    @RequiresPermissions("sys:role:normal")
    public Result<String> batchDeleteAgentTemplates(@RequestBody List<String> ids) {
        boolean deleted = agentTemplateService.removeByIds(ids);
        if (deleted) {
            return ResultUtils.success("批量删除成功");
        } else {
            return ResultUtils.error("批量删除模板失败");
        }
    }
}