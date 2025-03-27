package xiaozhi.modules.agent.controller;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.Parameters;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.AllArgsConstructor;
import org.apache.shiro.authz.annotation.RequiresPermissions;
import org.springframework.web.bind.annotation.*;
import xiaozhi.common.constant.Constant;
import xiaozhi.common.page.PageData;
import xiaozhi.common.user.UserDetail;
import xiaozhi.common.utils.ConvertUtils;
import xiaozhi.common.utils.Result;
import xiaozhi.modules.agent.dto.AgentCreateDTO;
import xiaozhi.modules.agent.dto.AgentUpdateDTO;
import xiaozhi.modules.agent.entity.AgentEntity;
import xiaozhi.modules.agent.service.AgentService;
import xiaozhi.modules.security.user.SecurityUser;

import java.util.Date;
import java.util.List;
import java.util.Map;

@Tag(name = "智能体管理")
@AllArgsConstructor
@RestController
@RequestMapping("/agent")
public class AgentController {
    private final AgentService agentService;
    
    @GetMapping("/list")
    @Operation(summary = "获取用户智能体列表")
    @RequiresPermissions("sys:role:normal")
    public Result<List<AgentEntity>> getUserAgents() {
        UserDetail user = SecurityUser.getUser();
        List<AgentEntity> agents = agentService.getUserAgents(user.getId());
        return new Result<List<AgentEntity>>().ok(agents);
    }
    
    @GetMapping("/all")
    @Operation(summary = "智能体列表（管理员）")
    @RequiresPermissions("sys:role:superAdmin")
    @Parameters({
            @Parameter(name = Constant.PAGE, description = "当前页码，从1开始", required = true),
            @Parameter(name = Constant.LIMIT, description = "每页显示记录数", required = true),
    })
    public Result<PageData<AgentEntity>> adminAgentList(
            @Parameter(hidden = true) @RequestParam Map<String, Object> params) {
        PageData<AgentEntity> page = agentService.adminAgentList(params);
        return new Result<PageData<AgentEntity>>().ok(page);
    }
    
    @GetMapping("/{id}")
    @Operation(summary = "获取智能体详情")
    @RequiresPermissions("sys:role:normal")
    public Result<AgentEntity> getAgentById(@PathVariable("id") String id) {
        AgentEntity agent = agentService.getAgentById(id);
        return new Result<AgentEntity>().ok(agent);
    }
    
    @PostMapping
    @Operation(summary = "创建智能体")
    @RequiresPermissions("sys:role:normal")
    public Result<Void> save(@RequestBody @Valid AgentCreateDTO dto) {
        AgentEntity entity = ConvertUtils.sourceToTarget(dto, AgentEntity.class);
        
        // 设置用户ID和创建者信息
        UserDetail user = SecurityUser.getUser();
        entity.setUserId(user.getId());
        entity.setCreator(user.getId());
        entity.setCreatedAt(new Date());
        
        // ID、智能体编码和排序会在Service层自动生成
        agentService.insert(entity);
        
        return new Result<>();
    }
    
    @PutMapping
    @Operation(summary = "更新智能体")
    @RequiresPermissions("sys:role:normal")
    public Result<Void> update(@RequestBody @Valid AgentUpdateDTO dto) {
        // 先查询现有实体
        AgentEntity existingEntity = agentService.getAgentById(dto.getId());
        if (existingEntity == null) {
            return new Result<Void>().error("智能体不存在");
        }
        
        // 只更新提供的非空字段
        if (dto.getAgentName() != null) {
            existingEntity.setAgentName(dto.getAgentName());
        }
        if (dto.getAgentCode() != null) {
            existingEntity.setAgentCode(dto.getAgentCode());
        }
        if (dto.getAsrModelId() != null) {
            existingEntity.setAsrModelId(dto.getAsrModelId());
        }
        if (dto.getVadModelId() != null) {
            existingEntity.setVadModelId(dto.getVadModelId());
        }
        if (dto.getLlmModelId() != null) {
            existingEntity.setLlmModelId(dto.getLlmModelId());
        }
        if (dto.getTtsModelId() != null) {
            existingEntity.setTtsModelId(dto.getTtsModelId());
        }
        if (dto.getTtsVoiceId() != null) {
            existingEntity.setTtsVoiceId(dto.getTtsVoiceId());
        }
        if (dto.getMemModelId() != null) {
            existingEntity.setMemModelId(dto.getMemModelId());
        }
        if (dto.getIntentModelId() != null) {
            existingEntity.setIntentModelId(dto.getIntentModelId());
        }
        if (dto.getSystemPrompt() != null) {
            existingEntity.setSystemPrompt(dto.getSystemPrompt());
        }
        if (dto.getLangCode() != null) {
            existingEntity.setLangCode(dto.getLangCode());
        }
        if (dto.getLanguage() != null) {
            existingEntity.setLanguage(dto.getLanguage());
        }
        if (dto.getSort() != null) {
            existingEntity.setSort(dto.getSort());
        }
        
        // 设置更新者信息
        UserDetail user = SecurityUser.getUser();
        existingEntity.setUpdater(user.getId());
        existingEntity.setUpdatedAt(new Date());
        
        agentService.updateById(existingEntity);
        
        return new Result<>();
    }
    
    @DeleteMapping("/{id}")
    @Operation(summary = "删除智能体")
    @RequiresPermissions("sys:role:normal")
    public Result<Void> delete(@PathVariable String id) {
        agentService.deleteById(id);
        return new Result<>();
    }
} 