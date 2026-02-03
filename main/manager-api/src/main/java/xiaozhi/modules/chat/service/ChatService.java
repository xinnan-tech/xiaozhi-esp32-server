package xiaozhi.modules.chat.service;

import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import xiaozhi.modules.knowledge.dto.chat.ChatCompletionRequest;

/**
 * 统一对话服务接口
 */
public interface ChatService {

    /**
     * 发起流式对话 (OpenAI 兼容)
     * 
     * @param request 对话请求
     * @param emitter SSE 发射器
     */
    void streamChat(ChatCompletionRequest request, SseEmitter emitter);
}
