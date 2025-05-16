package xiaozhi.modules.agent.controller;

import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import xiaozhi.common.utils.Result;
import xiaozhi.modules.agent.dto.AgentChatHistoryReportDTO;
import xiaozhi.modules.agent.service.biz.AgentChatHistoryBizService;

@Tag(name = "智能体聊天历史管理")
@RequiredArgsConstructor
@RestController
@RequestMapping("/agent/chat-history")
public class AgentChatHistoryController {
    private final AgentChatHistoryBizService agentChatHistoryBizService;

    /**
     * 小智服务聊天上报请求
     * <p>
     * 小智服务聊天上报请求，包含Base64编码的音频数据和相关信息。
     *
     * @param request 包含上传文件及相关信息的请求对象
     */
    @Operation(summary = "小智服务聊天上报请求")
    @PostMapping("/report")
    public Result<Boolean> uploadFile(@Valid @RequestBody AgentChatHistoryReportDTO request) {
        Boolean result = agentChatHistoryBizService.report(request);
        return new Result<Boolean>().ok(result);
    }
}
