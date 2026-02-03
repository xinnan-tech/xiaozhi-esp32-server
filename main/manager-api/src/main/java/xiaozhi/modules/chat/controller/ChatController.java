package xiaozhi.modules.chat.controller;

import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;
import xiaozhi.modules.chat.service.ChatService;
import xiaozhi.modules.knowledge.dto.chat.ChatCompletionRequest;

@Tag(name = "统一对话服务")
@RestController
@RequestMapping("/chat")
@RequiredArgsConstructor
public class ChatController {

    private final ChatService chatService;

    @Operation(summary = "发起流式对话 (OpenAI 兼容)")
    @PostMapping(value = "/completions", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter chatCompletions(@RequestBody ChatCompletionRequest request) {
        // 创建 SseEmitter，设置超时时间 (例如 5 分钟)
        SseEmitter emitter = new SseEmitter(5 * 60 * 1000L);

        // 异步执行 (虽然 SseEmitter 本身支持异步，但 service 内部最好也是非阻塞或快速返回)
        // 由于 postStream 是阻塞读取流的 (httpClient.send...transferTo)，
        // 我们需要在一个新线程中运行它，以免阻塞 Servlet 容器线程 (虽然 Servlet 3.1+ 支持 AsyncContext，SseEmitter
        // 会处理)
        // 但为了安全起见，通常 controller 方法返回 emitter 后，业务逻辑在另一个线程执行。

        // 简单起见，这里直接在一个新线程启动任务
        // 在生产环境中应使用线程池
        new Thread(() -> {
            try {
                chatService.streamChat(request, emitter);
            } catch (Exception e) {
                emitter.completeWithError(e);
            }
        }).start();

        return emitter;
    }
}
