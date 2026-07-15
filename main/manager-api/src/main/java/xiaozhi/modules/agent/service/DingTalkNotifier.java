package xiaozhi.modules.agent.service;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.security.InvalidKeyException;
import java.security.NoSuchAlgorithmException;
import java.util.Base64;
import java.util.HashMap;
import java.util.Map;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import cn.hutool.http.HttpUtil;
import cn.hutool.json.JSONUtil;
import lombok.extern.slf4j.Slf4j;

/**
 * 钉钉群机器人通知:角色不足兜底时通知管理员扩库。
 * webhook / secret 从 application.yml(growth.dingtalk-webhook / growth.dingtalk-secret)读取,
 * 该值通过环境变量 DINGTALK_WEBHOOK / DINGTALK_SECRET 注入(不落库明文)。
 * 安全模式:优先「加签」(secret 非空时按 HmacSHA256 生成 timestamp+sign 追加到 URL);
 * secret 为空则按「自定义关键字」模式直发(webhook 需已配关键字「角色匹配」)。
 * webhook 未配置则跳过,不阻塞主流程。
 */
@Slf4j
@Component
public class DingTalkNotifier {

    @Value("${growth.dingtalk-webhook:}")
    private String webhook;

    @Value("${growth.dingtalk-secret:}")
    private String secret;

    /**
     * 发送钉钉文本通知。webhook 未配置则跳过(不抛异常)。
     */
    public void notify(String content) {
        if (webhook == null || webhook.isBlank()) {
            log.warn("[dingtalk] webhook 未配置,跳过通知:{}", content);
            return;
        }
        try {
            Map<String, Object> text = new HashMap<>();
            text.put("content", content);
            Map<String, Object> body = new HashMap<>();
            body.put("msgtype", "text");
            body.put("text", text);
            String postUrl = buildSignedUrl(webhook, secret);
            String resp = HttpUtil.post(postUrl, JSONUtil.toJsonStr(body));
            log.info("[dingtalk] 通知已发送,响应:{}", resp);
        } catch (Exception e) {
            log.warn("[dingtalk] 通知发送失败:{}", e.getMessage());
        }
    }

    /**
     * 加签:secret 非空时在 webhook 后追加 &timestamp=...&sign=...
     * 算法:stringToSign = timestamp + "\n" + secret;sign = Base64(HmacSHA256(stringToSign, secret))
     */
    private String buildSignedUrl(String webhook, String secret) throws NoSuchAlgorithmException, InvalidKeyException {
        if (secret == null || secret.isBlank()) {
            return webhook; // 关键字模式
        }
        long timestamp = System.currentTimeMillis();
        String stringToSign = timestamp + "\n" + secret;
        Mac mac = Mac.getInstance("HmacSHA256");
        mac.init(new SecretKeySpec(secret.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
        byte[] signData = mac.doFinal(stringToSign.getBytes(StandardCharsets.UTF_8));
        String sign = Base64.getEncoder().encodeToString(signData);
        String encodedSign = URLEncoder.encode(sign, StandardCharsets.UTF_8);
        String sep = webhook.contains("?") ? "&" : "?";
        return webhook + sep + "timestamp=" + timestamp + "&sign=" + encodedSign;
    }
}
