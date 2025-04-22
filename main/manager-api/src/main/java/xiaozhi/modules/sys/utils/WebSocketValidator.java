package xiaozhi.modules.sys.utils;

import java.net.URI;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;
import java.util.regex.Pattern;

import org.apache.commons.lang3.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.web.socket.client.WebSocketClient;
import org.springframework.web.socket.client.standard.StandardWebSocketClient;

public class WebSocketValidator {
    private static final Logger logger = LoggerFactory.getLogger(WebSocketValidator.class);

    // WebSocket URL正则表达式
    private static final Pattern WS_URL_PATTERN = Pattern
            .compile("^wss?://[\\w.-]+(?:\\.[\\w.-]+)*(?::\\d+)?(?:/[\\w.-]*)*$");

    /**
     * 验证WebSocket地址格式
     * 
     * @param url WebSocket地址
     * @return 是否有效
     */
    public static boolean validateUrlFormat(String url) {
        if (StringUtils.isBlank(url)) {
            return false;
        }
        return WS_URL_PATTERN.matcher(url.trim()).matches();
    }

    /**
     * 测试WebSocket连接
     * 
     * @param url WebSocket地址
     * @return 是否可连接
     */
    public static boolean testConnection(String url) {
        if (!validateUrlFormat(url)) {
            return false;
        }

        try {
            WebSocketClient client = new StandardWebSocketClient();
            CompletableFuture<Boolean> future = new CompletableFuture<>();

            client.doHandshake(new WebSocketTestHandler(future), null, URI.create(url));

            // 等待最多5秒获取连接结果
            return future.get(5, TimeUnit.SECONDS);
        } catch (Exception e) {
            logger.error("WebSocket连接测试失败: {}", url, e);
            return false;
        }
    }
}