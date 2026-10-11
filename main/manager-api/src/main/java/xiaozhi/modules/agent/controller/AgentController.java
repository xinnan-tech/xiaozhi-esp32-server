package xiaozhi.modules.agent.controller;

import java.util.List;
import java.util.Map;
import java.util.UUID;

import org.apache.commons.lang3.StringUtils;
import org.apache.shiro.authz.annotation.RequiresPermissions;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
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

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.Parameters;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.AllArgsConstructor;
import xiaozhi.common.constant.Constant;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.page.PageData;
import xiaozhi.common.redis.RedisKeys;
import xiaozhi.common.redis.RedisUtils;
import xiaozhi.common.user.UserDetail;
import xiaozhi.common.utils.JsonUtils;
import xiaozhi.common.utils.Result;
import xiaozhi.common.utils.ResultUtils;
import xiaozhi.modules.agent.dto.AgentChatHistoryDTO;
import xiaozhi.modules.agent.dto.AgentChatSessionDTO;
import xiaozhi.modules.agent.dto.AgentCreateDTO;
import xiaozhi.modules.agent.dto.AgentDTO;
import xiaozhi.modules.agent.dto.AgentMemoryDTO;
import xiaozhi.modules.agent.dto.AgentUpdateDTO;
import xiaozhi.modules.agent.entity.AgentEntity;
import xiaozhi.modules.agent.entity.AgentTemplateEntity;
import xiaozhi.modules.agent.dto.AgentTagDTO;
import xiaozhi.modules.agent.entity.AgentTagEntity;
import xiaozhi.modules.agent.service.AgentTagService;
import xiaozhi.modules.agent.service.AgentChatAudioService;
import xiaozhi.modules.agent.service.AgentChatHistoryService;
import xiaozhi.modules.agent.service.AgentChatSummaryService;
import xiaozhi.modules.agent.service.AgentService;
import xiaozhi.modules.agent.service.AgentTemplateService;
import xiaozhi.modules.agent.vo.AgentChatHistoryUserVO;
import xiaozhi.modules.agent.vo.AgentInfoVO;
import xiaozhi.modules.security.user.SecurityUser;

@Tag(name = "Agent management")
@AllArgsConstructor
@RestController
@RequestMapping("/agent")
public class AgentController {
    private static final long AUDIO_PLAY_TOKEN_EXPIRE_SECONDS = 300L;

    private final AgentService agentService;
    private final AgentTemplateService agentTemplateService;
    private final AgentChatHistoryService agentChatHistoryService;
    private final AgentChatAudioService agentChatAudioService;
    private final AgentChatSummaryService agentChatSummaryService;
    private final RedisUtils redisUtils;
    private final AgentTagService agentTagService;

    private void requireAgentPermission(String agentId) {
        if (!agentService.checkAgentPermission(agentId, SecurityUser.getUserId())) {
            throw new RenException(ErrorCode.NO_PERMISSION);
        }
    }

    private String requireSessionAgent(String sessionId) {
        String agentId = agentChatHistoryService.getAgentIdBySessionId(sessionId);
        if (StringUtils.isBlank(agentId)) {
            throw new RenException(ErrorCode.AGENT_NOT_FOUND);
        }
        agentService.getAgentById(agentId);
        return agentId;
    }

    private String requireAudioPermission(String audioId) {
        String agentId = agentChatHistoryService.getAgentIdByAudioId(audioId);
        if (StringUtils.isBlank(agentId)) {
            throw new RenException(ErrorCode.NO_PERMISSION);
        }
        requireAgentPermission(agentId);
        return agentId;
    }

    @GetMapping("/list")
    @Operation(summary = "Get user agent list")
    @RequiresPermissions("sys:role:normal")
    public Result<List<AgentDTO>> getUserAgents(
            @RequestParam(value = "keyword", required = false) String keyword,
            @RequestParam(value = "searchType", defaultValue = "name") String searchType) {
        UserDetail user = SecurityUser.getUser();

        // Directly call the integrated getUserAgents method, no need to distinguish between search and standard queries
        List<AgentDTO> agents = agentService.getUserAgents(user.getId(), keyword, searchType);
        return new Result<List<AgentDTO>>().ok(agents);
    }

    @GetMapping("/all")
    @Operation(summary = "Agent list (Admin)")
    @RequiresPermissions("sys:role:superAdmin")
    @Parameters({
            @Parameter(name = Constant.PAGE, description = "Current page number, starting from 1", required = true),
            @Parameter(name = Constant.LIMIT, description = "Records per page", required = true),
    })
    public Result<PageData<AgentEntity>> adminAgentList(
            @Parameter(hidden = true) @RequestParam Map<String, Object> params) {
        PageData<AgentEntity> page = agentService.adminAgentList(params);
        return new Result<PageData<AgentEntity>>().ok(page);
    }

    @GetMapping("/{id}")
    @Operation(summary = "Get agent details")
    @RequiresPermissions("sys:role:normal")
    public Result<AgentInfoVO> getAgentById(@PathVariable("id") String id) {
        AgentInfoVO agent = agentService.getAgentById(id, SecurityUser.getUserId());
        return ResultUtils.success(agent);
    }

    @PostMapping
    @Operation(summary = "Create Agent")
    @RequiresPermissions("sys:role:normal")
    public Result<String> save(@RequestBody @Valid AgentCreateDTO dto) {
        String agentId = agentService.createAgent(dto);
        return new Result<String>().ok(agentId);
    }

    @PutMapping("/saveMemory/{macAddress}")
    @Operation(summary = "Update agent by device ID")
    @RequiresPermissions("sys:role:normal")
    public Result<Void> updateByDeviceId(@PathVariable String macAddress, @RequestBody @Valid AgentMemoryDTO dto) {
        agentService.updateAgentMemoryByDeviceMacAddress(macAddress, dto, SecurityUser.getUserId());
        return new Result<Void>().ok(null);
    }

    @PostMapping("/chat-summary/{sessionId}/save")
    @Operation(summary = "Generate and save chat history summary based on session ID (async execution)")
    public Result<Void> generateAndSaveChatSummary(@PathVariable String sessionId) {
        requireSessionAgent(sessionId);
        try {
            // Execute summary generation asynchronously and return success immediately
            new Thread(() -> {
                try {
                    agentChatSummaryService.generateAndSaveChatSummary(sessionId);
                    System.out.println("Async chat history summary completed for session " + sessionId);
                } catch (Exception e) {
                    System.err.println("Failed to summarize chat history for async session " + sessionId + ": " + e.getMessage());
                }
            }).start();

            // Return success response immediately without waiting for summary generation
            return new Result<Void>().ok(null);
        } catch (Exception e) {
            return new Result<Void>().error("Failed to start async summary generation task: " + e.getMessage());
        }
    }

    @PostMapping("/chat-title/{sessionId}/generate")
    @Operation(summary = "Generate chat title based on session ID")
    public Result<Void> generateAndSaveChatTitle(@PathVariable String sessionId) {
        requireSessionAgent(sessionId);
        agentChatSummaryService.generateAndSaveChatTitle(sessionId);
        return new Result<Void>().ok(null);
    }

    @PutMapping("/{id}")
    @Operation(summary = "Update agent")
    @RequiresPermissions("sys:role:normal")
    public Result<Void> update(@PathVariable String id, @RequestBody @Valid AgentUpdateDTO dto) {
        agentService.updateAgentById(id, dto, SecurityUser.getUserId());
        return new Result<>();
    }

    @DeleteMapping("/{id}")
    @Operation(summary = "Delete Agent")
    @RequiresPermissions("sys:role:normal")
    public Result<Void> delete(@PathVariable String id) {
        agentService.deleteAgentById(id, SecurityUser.getUserId());
        return new Result<>();
    }

    @GetMapping("/template")
    @Operation(summary = "Agent template list")
    @RequiresPermissions("sys:role:normal")
    public Result<List<AgentTemplateEntity>> templateList() {
        List<AgentTemplateEntity> list = agentTemplateService
                .list(new QueryWrapper<AgentTemplateEntity>().orderByAsc("sort"));
        return new Result<List<AgentTemplateEntity>>().ok(list);
    }

    @GetMapping("/{id}/sessions")
    @Operation(summary = "Get Agent session list")
    @RequiresPermissions("sys:role:normal")
    @Parameters({
            @Parameter(name = Constant.PAGE, description = "Current page number, starting from 1", required = true),
            @Parameter(name = Constant.LIMIT, description = "Records per page", required = true),
    })
    public Result<PageData<AgentChatSessionDTO>> getAgentSessions(
            @PathVariable("id") String id,
            @Parameter(hidden = true) @RequestParam Map<String, Object> params) {
        requireAgentPermission(id);
        params.put("agentId", id);
        PageData<AgentChatSessionDTO> page = agentChatHistoryService.getSessionListByAgentId(params);
        return new Result<PageData<AgentChatSessionDTO>>().ok(page);
    }

    @GetMapping("/{id}/chat-history/{sessionId}")
    @Operation(summary = "Get agent chat history")
    @RequiresPermissions("sys:role:normal")
    public Result<List<AgentChatHistoryDTO>> getAgentChatHistory(
            @PathVariable("id") String id,
            @PathVariable("sessionId") String sessionId) {
        // Get current user
        UserDetail user = SecurityUser.getUser();

        // Check permissions
        if (!agentService.checkAgentPermission(id, user.getId())) {
            return new Result<List<AgentChatHistoryDTO>>().error("No permission to view this Agent's chat history.");
        }

        // Query chat history
        List<AgentChatHistoryDTO> result = agentChatHistoryService.getChatHistoryBySessionId(id, sessionId);
        return new Result<List<AgentChatHistoryDTO>>().ok(result);
    }

    @GetMapping("/{id}/chat-history/user")
    @Operation(summary = "Get Agent chat history (user)")
    @RequiresPermissions("sys:role:normal")
    public Result<List<AgentChatHistoryUserVO>> getRecentlyFiftyByAgentId(
            @PathVariable("id") String id) {
        // Get current user
        UserDetail user = SecurityUser.getUser();

        // Check permissions
        if (!agentService.checkAgentPermission(id, user.getId())) {
            return new Result<List<AgentChatHistoryUserVO>>().error("No permission to view this Agent's chat history.");
        }

        // Query chat history
        List<AgentChatHistoryUserVO> data = agentChatHistoryService.getRecentlyFiftyByAgentId(id);
        return new Result<List<AgentChatHistoryUserVO>>().ok(data);
    }

    @GetMapping("/{id}/chat-history/audio")
    @Operation(summary = "Get audio content")
    @RequiresPermissions("sys:role:normal")
    public Result<String> getContentByAudioId(
            @PathVariable("id") String id) {
        requireAudioPermission(id);
        // Query chat history
        String data = agentChatHistoryService.getContentByAudioId(id);
        return new Result<String>().ok(data);
    }

    @PostMapping("/audio/{audioId}")
    @Operation(summary = "Get audio download ID")
    @RequiresPermissions("sys:role:normal")
    public Result<String> getAudioId(@PathVariable("audioId") String audioId) {
        requireAudioPermission(audioId);
        byte[] audioData = agentChatAudioService.getAudio(audioId);
        if (audioData == null) {
            return new Result<String>().error("Audio not found");
        }
        String uuid = UUID.randomUUID().toString();
        redisUtils.set(RedisKeys.getAgentAudioIdKey(uuid), audioId, AUDIO_PLAY_TOKEN_EXPIRE_SECONDS);
        return new Result<String>().ok(uuid);
    }

    @GetMapping("/play/{uuid}")
    @Operation(summary = "Play audio")
    public ResponseEntity<byte[]> playAudio(@PathVariable("uuid") String uuid) {

        String audioId = (String) redisUtils.get(RedisKeys.getAgentAudioIdKey(uuid));
        if (StringUtils.isBlank(audioId)) {
            return ResponseEntity.notFound().build();
        }

        byte[] audioData = agentChatAudioService.getAudio(audioId);
        if (audioData == null) {
            return ResponseEntity.notFound().build();
        }
        redisUtils.delete(RedisKeys.getAgentAudioIdKey(uuid));
        return ResponseEntity.ok()
                .contentType(MediaType.APPLICATION_OCTET_STREAM)
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"play.wav\"")
                .body(audioData);
    }

    @PostMapping("/tag")
    @Operation(summary = "Create Tag")
    @RequiresPermissions("sys:role:normal")
    public Result<AgentTagEntity> createTag(@RequestBody Map<String, String> params) {
        String tagName = params.get("tagName");
        if (StringUtils.isBlank(tagName)) {
            return new Result<AgentTagEntity>().error("Tag name cannot be empty");
        }
        AgentTagEntity tag = agentTagService.saveTag(tagName);
        return new Result<AgentTagEntity>().ok(tag);
    }

    @GetMapping("/tag/list")
    @Operation(summary = "Get all tags list")
    @RequiresPermissions("sys:role:normal")
    public Result<List<AgentTagDTO>> getAllTags() {
        List<AgentTagDTO> tags = agentTagService.getAllTags();
        return new Result<List<AgentTagDTO>>().ok(tags);
    }

    @DeleteMapping("/tag/{id}")
    @Operation(summary = "Delete Tag")
    @RequiresPermissions("sys:role:normal")
    public Result<Void> deleteTag(@PathVariable String id) {
        agentTagService.deleteTag(id);
        return new Result<Void>().ok(null);
    }

    @GetMapping("/{id}/tags")
    @Operation(summary = "Get agent tags")
    @RequiresPermissions("sys:role:normal")
    public Result<List<AgentTagDTO>> getAgentTags(@PathVariable String id) {
        requireAgentPermission(id);
        List<AgentTagDTO> tags = agentTagService.getTagsByAgentId(id);
        return new Result<List<AgentTagDTO>>().ok(tags);
    }

    @PutMapping("/{id}/tags")
    @Operation(summary = "Save agent tags")
    @RequiresPermissions("sys:role:normal")
    public Result<Void> saveAgentTags(@PathVariable String id, @RequestBody Map<String, Object> params) {
        requireAgentPermission(id);
        List<String> tagIds = JsonUtils.toList(params.get("tagIds"), String.class);
        List<String> tagNames = JsonUtils.toList(params.get("tagNames"), String.class);
        AgentUpdateDTO dto = new AgentUpdateDTO();
        dto.setTagIds(tagIds);
        dto.setTagNames(tagNames);
        agentService.updateAgentById(id, dto);
        return new Result<Void>().ok(null);
    }

}
