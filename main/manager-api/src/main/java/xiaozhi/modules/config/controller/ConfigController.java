package xiaozhi.modules.config.controller;

import java.util.Map;

import org.apache.commons.lang3.StringUtils;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.AllArgsConstructor;
import xiaozhi.common.constant.Constant;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.utils.Result;
import xiaozhi.common.validator.ValidatorUtils;
import xiaozhi.modules.agent.service.AgentService;
import xiaozhi.modules.config.dto.AgentModelsDTO;
import xiaozhi.modules.sys.dto.ConfigSecretDTO;
import xiaozhi.modules.sys.service.SysParamsService;

/**
 * xiaozhi-server 配置获取
 *
 * @since 1.0.0
 */
@RestController
@RequestMapping("config")
@Tag(name = "参数管理")
@AllArgsConstructor
public class ConfigController {
    private final SysParamsService sysParamsService;
    private final AgentService agentService;

    @PostMapping("server-base")
    @Operation(summary = "获取配置")
    public Result<Object> getConfig(@RequestBody ConfigSecretDTO dto) {
        // 效验数据
        ValidatorUtils.validateEntity(dto);
        checkSecret(dto.getSecret());
        Object config = sysParamsService.getConfig();
        return new Result<Object>().ok(config);
    }

    @PostMapping("agent-models")
    @Operation(summary = "获取智能体模型")
    public Result<Object> getAgentModels(@RequestBody AgentModelsDTO dto) {
        // 效验数据
        ValidatorUtils.validateEntity(dto);
        checkSecret(dto.getSecret());
        Map<String, Object> models = agentService.getAgentModelsByMac(dto.getMacAddress());
        return new Result<Object>().ok(models);
    }

    private void checkSecret(String secret) {
        String secretParam = sysParamsService.getValue(Constant.SERVER_SECRET, true);
        // 验证密钥
        if (StringUtils.isBlank(secret) || !secret.equals(secretParam)) {
            throw new RenException("密钥错误");
        }
    }
}
