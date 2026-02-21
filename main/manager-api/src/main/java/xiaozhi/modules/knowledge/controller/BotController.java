//package xiaozhi.modules.knowledge.controller;
//
//import java.util.HashMap;
//import java.util.Map;
//
//import org.apache.commons.lang3.StringUtils;
//import org.springframework.http.MediaType;
//import org.springframework.web.bind.annotation.PathVariable;
//import org.springframework.web.bind.annotation.PostMapping;
//import org.springframework.web.bind.annotation.RequestBody;
//import org.springframework.web.bind.annotation.RequestMapping;
//import org.springframework.web.bind.annotation.RestController;
//import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;
//
//import io.swagger.v3.oas.annotations.Operation;
//import io.swagger.v3.oas.annotations.tags.Tag;
//import lombok.RequiredArgsConstructor;
//import lombok.extern.slf4j.Slf4j;
//import xiaozhi.common.exception.ErrorCode;
//import xiaozhi.common.exception.RenException;
//import xiaozhi.modules.agent.entity.AgentEntity;
//import xiaozhi.modules.agent.service.AgentService;
//import xiaozhi.modules.knowledge.dto.bot.BotDTO;
//import xiaozhi.modules.knowledge.rag.KnowledgeBaseAdapter;
//import xiaozhi.modules.knowledge.rag.KnowledgeBaseAdapterFactory;
//import xiaozhi.modules.knowledge.service.KnowledgeBaseService;
//import xiaozhi.modules.model.entity.ModelConfigEntity;
//import xiaozhi.modules.model.service.ModelConfigService;
//
//@Tag(name = "外部机器人服务")
//@RestController
//@RequestMapping("/api/v1") // 保持与外部 API 一致的风格，或者映射到 RAGFlow 风格
//@RequiredArgsConstructor
//@Slf4j
//public class BotController {//todo:这个类还有待完成，待完善。这里的agent和其他模块的agent不一样，这里的agent是存在于ragflow中等agent/工作流，不独立存在，需要借助rag作为平台进行交流交互
//
//    private final AgentService agentService;
//    private final ModelConfigService modelConfigService;
//    private final KnowledgeBaseService knowledgeBaseService;
//
//    // SearchBot (暂未完全实现，预留接口)
//    @Operation(summary = "SearchBot 提问")
//    @PostMapping(value = "/searchbots/ask", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
//    public SseEmitter searchBotAsk(@RequestBody BotDTO.SearchAskReq request) {
//        // TODO: SearchBot 通常需要指定 Dataset 或 KnowledgeBase
//        // 这里需要明确 SearchBot 的 ID 来源。
//        // 暂时返回未实现
//        throw new RenException("SearchBot API 暂未开放");
//    }
//
//    // AgentBot
//    @Operation(summary = "AgentBot 对话 (流式)")
//    @PostMapping(value = "/agentbots/{id}/completions", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
//    public SseEmitter agentBotCompletion(@PathVariable("id") String agentId,
//            @RequestBody BotDTO.AgentCompletionReq request) {
//        SseEmitter emitter = new SseEmitter(5 * 60 * 1000L); // 5 min timeout
//
//        new Thread(() -> {
//            try {
//                // 1. 获取本地 Agent
//                // 注意：这里的 id 是本地 AgentId
//                AgentEntity agent = agentService.getAgentById(agentId); // getAgentById actually returns VO but we need
//                                                                        // Entity fields
//                // 直接查 DB 或用 Service
//                // Service returns AgentInfoVO, let's better use getById from BaseService (which
//                // returns Entity) if exposed
//                // AgentService extends BaseService<AgentEntity>
//                AgentEntity entity = agentService.selectById(agentId);
//
//                if (entity == null) {
//                    throw new RenException(ErrorCode.AGENT_NOT_FOUND);
//                }
//
//                // 2. 获取关联的 RAG 配置
//                String llmModelId = entity.getLlmModelId();
//                if (StringUtils.isBlank(llmModelId)) {
//                    throw new RenException("Agent未配置LLM模型");
//                }
//
//                // 3. 所有的 AgentBot 请求都通过关联的 RAGConfig 下发
//                Map<String, Object> ragConfig = knowledgeBaseService.getRAGConfig(llmModelId);
//                String adapterType = (String) ragConfig.getOrDefault("type", "ragflow");
//                KnowledgeBaseAdapter adapter = KnowledgeBaseAdapterFactory.getAdapter(adapterType, ragConfig);
//
//                // 4. 发起请求
//                // 注意：这里需要传递给 RAGFlow 的 Agent ID 可能是 config 中的某些字段，
//                // 或者我们这里构建的 Agent 实际上是 RAGFlow 中的 Agent？
//                // 根据 Deep Dive，ChatService 是自己组装 prompt 调用 chat/completions。
//                // 而 BotController 似乎旨在暴露 RAGFlow 的 AgentBot 能力。
//                // 如果我们是“Java主导”，那么其实这里的逻辑应该和 ChatService 类似：
//                // 即：我们自己组装参数，调用 RAGFlow 的 Chat/Completion 接口，而不是调用 AgentBot 接口。
//                // 除非 RAGFlow 侧真的有一个 "Agent" 对象对应我们的 Agent。
//                // 鉴于 Step 8 中我们决定 "Java-Side Master"，且 RAGFlow 是推理引擎，
//                // 我们应该复用 ChatService 的逻辑，或者调用 POST /chat/completions (RAGFlow)
//
//                // 但为了符合 BotDTO 的定义 (/agentbots/{id}/completions)，我们这里模拟这个行为
//                // 且尽量复用 ChatService 的流式能力。
//
//                // 这里的 adapter.postAgentBotCompletion 实现的是调用 /api/v1/agentbots/{id}/completions
//                // 这要求 RAGFlow 侧必须存在这个 ID。
//                // 但我们的 Agent 是本地的。
//                // **修正策略**：
//                // 如果 RAGFlow 侧没有对应 Agent，我们不能调这个接口。
//                // 我们应该降级为调用 Chat 接口 (/chat/completions)，带上 system prompt。
//
//                // 出于本步骤目标 "Bot Service (Public Access)"，我们为了兼容外部 Bot 协议，
//                // 应该要把本地请求转换为 RAGFlow 的 Chat 请求。
//
//                Map<String, Object> chatBody = new HashMap<>();
//                chatBody.put("messages", java.util.List.of(
//                        Map.of("role", "user", "content", request.getQuestion())));
//                chatBody.put("stream", request.getStream());
//                chatBody.put("model", entity.getAgentName()); // Mock name
//                if (StringUtils.isNotBlank(entity.getSystemPrompt())) {
//                    chatBody.put("system_prompt", entity.getSystemPrompt());
//                }
//
//                adapter.postStream("/api/v1/chat/completions", chatBody, line -> {
//                    try {
//                        if (line.startsWith("data:")) {
//                            String dataContent = line.substring(5).trim();
//                            if (!"[DONE]".equals(dataContent)) {
//                                emitter.send(SseEmitter.event().data(dataContent));
//                            }
//                        }
//                    } catch (Exception e) {
//                        log.error("SSE Error", e);
//                        throw new RuntimeException(e);
//                    }
//                });
//
//                emitter.send(SseEmitter.event().data("[DONE]"));
//                emitter.complete();
//
//            } catch (Exception e) {
//                log.error("AgentBot Error", e);
//                try {
//                    emitter.send(SseEmitter.event().name("error").data(e.getMessage()));
//                    emitter.completeWithError(e);
//                } catch (Exception ex) {
//                    // ignore
//                }
//            }
//        }).start();
//
//        return emitter;
//    }
//}
