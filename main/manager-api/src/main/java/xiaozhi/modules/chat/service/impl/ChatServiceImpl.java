package xiaozhi.modules.chat.service.impl;

import java.io.IOException;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import com.fasterxml.jackson.databind.ObjectMapper;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.utils.JsonUtils;
import xiaozhi.modules.agent.entity.AgentEntity;
import xiaozhi.modules.agent.service.AgentService;
import xiaozhi.modules.chat.service.ChatService;
import xiaozhi.modules.knowledge.dto.chat.ChatCompletionRequest;
import xiaozhi.modules.knowledge.rag.KnowledgeBaseAdapter;
import xiaozhi.modules.knowledge.rag.KnowledgeBaseAdapterFactory;
import xiaozhi.modules.knowledge.service.KnowledgeBaseService;

@Slf4j
@Service
@RequiredArgsConstructor
public class ChatServiceImpl implements ChatService {

    private final AgentService agentService;
    private final KnowledgeBaseService knowledgeBaseService;
    private final ObjectMapper objectMapper = new ObjectMapper();

    @Override
    public void streamChat(ChatCompletionRequest request, SseEmitter emitter) {
        try {
            // 1. 基础校验
            String agentId = request.getModel();
            if (StringUtils.isBlank(agentId)) {
                sendError(emitter, "Model (Agent ID) is required");
                return;
            }

            // 2. 获取智能体信息
            AgentEntity agent = agentService.getAgentById(agentId); // 这里假设 getAgentById 会返回 Entiry or DTO
            if (agent == null) {
                sendError(emitter, "Agent not found");
                return;
            }

            // 3. 解析 RAG 配置 (从智能体关联的 LLM 模型或知识库配置中获取)
            // 这里我们需要确定连接 RAGFlow 的凭证。
            // 假设 Agent 关联了 ragModelId 或者我们直接使用系统默认 RAG 配置，
            // 或者是从 Agent 的 KnowledgeBase Link 中获取。
            // 鉴于目前逻辑，我们尝试获取 Agent 关联的 LLM 模型配置，如果它是 RAG 类型。
            // 或者，我们假设 request 中隐含了 target 知识库。
            // 但标准 Chat 接口只传 model。
            // 我们暂时使用 Agent 的 llmModelId 对应的配置，如果它是 OpenAI 兼容的 RAGFlow。

            String ragModelId = agent.getLlmModelId(); // 假设 Agent 的 LLM 模型指向 RAGFlow
            if (StringUtils.isBlank(ragModelId)) {
                sendError(emitter, "Agent LLM configuration missing");
                return;
            }

            Map<String, Object> ragConfig = knowledgeBaseService.getRAGConfig(ragModelId);

            // 提取适配器类型
            String adapterType = (String) ragConfig.getOrDefault("type", "ragflow");
            KnowledgeBaseAdapter adapter = KnowledgeBaseAdapterFactory.getAdapter(adapterType, ragConfig);

            // 4. 构建透传给 RAGFlow 的请求体
            Map<String, Object> ragBody = new HashMap<>();
            ragBody.put("messages", request.getMessages());
            ragBody.put("stream", true);

            // 注入参数 (优先使用请求中的，否则使用配置中的默认值)
            if (request.getTemperature() != null) {
                ragBody.put("temperature", request.getTemperature());
            }
            // 注入 system prompt (从 Agent 配置)
            if (StringUtils.isNotBlank(agent.getSystemPrompt())) {
                ragBody.put("system_prompt", agent.getSystemPrompt());
            }

            // RAGFlow 特有参数，如 quote, doc_ids 等，视业务需求注入
            if (request.getExtra() != null) {
                ragBody.putAll(request.getExtra());
            }

            // 5. 发起流式请求
            // Endpoint: 假设 RAGFlow 兼容 OpenAI 格式或有特定 Chat 接口
            // 这里使用 /api/v1/chat/completions 作为尝试
            String endpoint = "/api/v1/chat/completions";

            adapter.postStream(endpoint, ragBody, line -> {
                try {
                    // RAGFlow 返回的 SSE 数据 line 通常是 "data: {...}"
                    // 我们需要透传或做简单转换
                    if (line.startsWith("data:")) {
                        String dataContent = line.substring(5).trim();
                        if ("[DONE]".equals(dataContent)) {
                            return; // 暂不处理 DONE，最后统一 complete
                        }

                        // 尝试解析并重新包装，确保格式正确 (或者直接透传如果格式兼容)
                        // 这里做简单透传验证
                        emitter.send(SseEmitter.event().data(dataContent));
                    }
                } catch (IOException e) {
                    log.error("SSE send error", e);
                    // Connection likely closed by client
                    throw new RuntimeException("Client disconnected");
                }
            });

            // 结束
            emitter.send(SseEmitter.event().data("[DONE]"));
            emitter.complete();

        } catch (Exception e) {
            log.error("Stream chat error", e);
            sendError(emitter, e.getMessage());
        }
    }

    private void sendError(SseEmitter emitter, String msg) {
        try {
            Map<String, Object> error = new HashMap<>();
            error.put("error", msg);
            emitter.send(SseEmitter.event().name("error").data(error));
            emitter.completeWithError(new RuntimeException(msg));
        } catch (IOException e) {
            log.error("Error sending error message", e);
        }
    }
}
