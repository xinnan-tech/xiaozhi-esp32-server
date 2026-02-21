package xiaozhi.modules.knowledge.rag;

import java.time.Duration;
import java.nio.charset.StandardCharsets;
import java.util.Collections;
import java.util.Map;

import org.springframework.boot.web.client.RestTemplateBuilder;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestTemplate;

import com.fasterxml.jackson.databind.ObjectMapper;

import lombok.extern.slf4j.Slf4j;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;

/**
 * RAGFlow HTTP Client
 * 统一处理HTTP通信、鉴权、超时与错误解析
 */
@Slf4j
public class RAGFlowClient {

    private final String baseUrl;
    private final String apiKey;
    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper;

    // 默认超时时间 (秒)
    private static final int DEFAULT_TIMEOUT = 30;

    public RAGFlowClient(String baseUrl, String apiKey) {
        this(baseUrl, apiKey, DEFAULT_TIMEOUT);
    }

    public RAGFlowClient(String baseUrl, String apiKey, int timeoutSeconds) {
        this.baseUrl = baseUrl.endsWith("/") ? baseUrl.substring(0, baseUrl.length() - 1) : baseUrl;
        this.apiKey = apiKey;
        this.objectMapper = new ObjectMapper();
        // [Reinforce] 兼容 RAGFlow 返回的 RFC 1123 日期格式 (如: Tue, 10 Feb 2026 10:27:35 GMT)
        this.objectMapper
                .setDateFormat(new java.text.SimpleDateFormat("EEE, dd MMM yyyy HH:mm:ss 'GMT'", java.util.Locale.US));
        this.objectMapper.setTimeZone(java.util.TimeZone.getTimeZone("GMT"));

        // 优先从 Spring 上下文中获取池化的 RestTemplate Bean (Issue 3: 连接池化)
        RestTemplate pooledTemplate = null;
        try {
            pooledTemplate = xiaozhi.common.utils.SpringContextUtils.getBean(RestTemplate.class);
        } catch (Exception e) {
            log.warn("无法从 SpringContext 获取池化 RestTemplate，将退化为简单连接模式: {}", e.getMessage());
        }

        if (false) { // Force new RestTemplate for debugging
            this.restTemplate = pooledTemplate;
            log.debug("RAGFlowClient 已成功挂载全局池化 RestTemplate");
        } else {
            // 兜底方案：配置超时并创建简单 RestTemplate
            log.info("RAGFlowClient 初始化: 使用独立 RestTemplate (Debug Mode)");
            org.springframework.http.client.SimpleClientHttpRequestFactory factory = new org.springframework.http.client.SimpleClientHttpRequestFactory();
            factory.setConnectTimeout(timeoutSeconds * 1000);
            factory.setReadTimeout(timeoutSeconds * 1000);
            this.restTemplate = new RestTemplate(factory);
        }
    }

    /**
     * 发送 GET 请求
     */
    public Map<String, Object> get(String endpoint, Map<String, Object> queryParams) {
        String url = buildUrl(endpoint, queryParams);
        log.debug("GET {}", url);
        return execute(url, HttpMethod.GET, null);
    }

    /**
     * 发送 POST 请求 (JSON)
     */
    public Map<String, Object> post(String endpoint, Object body) {
        String url = buildUrl(endpoint, null);
        log.info("RAGFlow Client POST Request: URL={}, BodyType={}", url,
                body != null ? body.getClass().getName() : "null");
        try {
            return execute(url, HttpMethod.POST, body);
        } catch (Exception e) {
            log.error("RAGFlow Client POST Failed: URL={}", url, e);
            throw e;
        }
    }

    /**
     * 发送 DELETE 请求
     */
    public Map<String, Object> delete(String endpoint, Object body) {
        String url = buildUrl(endpoint, null);
        log.debug("DELETE {}", url);
        return execute(url, HttpMethod.DELETE, body);
    }

    /**
     * 发送 PUT 请求
     */
    public Map<String, Object> put(String endpoint, Object body) {
        String url = buildUrl(endpoint, null);
        log.debug("PUT {}", url);
        return execute(url, HttpMethod.PUT, body);
    }

    /**
     * 发送 Multipart 请求 (文件上传)
     */
    public Map<String, Object> postMultipart(String endpoint, MultiValueMap<String, Object> parts) {
        String url = buildUrl(endpoint, null);
        log.debug("POST MULTIPART {}", url);

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.MULTIPART_FORM_DATA);
        headers.setBearerAuth(apiKey);
        // 为了防止中文文件名乱码，某些环境可能需要设置 Charset，但在 Multipart 中通常由 Part header 控制

        HttpEntity<MultiValueMap<String, Object>> requestEntity = new HttpEntity<>(parts, headers);

        return doExecute(url, HttpMethod.POST, requestEntity);
    }

    private Map<String, Object> execute(String url, HttpMethod method, Object body) {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        headers.setBearerAuth(apiKey);
        // 强制 UTF-8
        headers.setAcceptCharset(Collections.singletonList(StandardCharsets.UTF_8));

        HttpEntity<Object> requestEntity = new HttpEntity<>(body, headers);
        return doExecute(url, method, requestEntity);
    }

    private Map<String, Object> doExecute(String url, HttpMethod method, HttpEntity<?> requestEntity) {
        try {
            ResponseEntity<String> response = restTemplate.exchange(url, method, requestEntity, String.class);

            if (!response.getStatusCode().is2xxSuccessful()) {
                log.error("RAGFlow API Error Status: {}", response.getStatusCode());
                throw new RenException(ErrorCode.RAG_API_ERROR, "HTTP " + response.getStatusCode());
            }

            String responseBody = response.getBody();
            if (responseBody == null) {
                throw new RenException(ErrorCode.RAG_API_ERROR, "Empty Response");
            }

            @SuppressWarnings("unchecked")
            Map<String, Object> map = objectMapper.readValue(responseBody, Map.class);

            Integer code = (Integer) map.get("code");
            if (code != null && code != 0) {
                String msg = (String) map.get("message");
                log.error("RAGFlow Business Error: code={}, msg={}", code, msg);
                throw new RenException(ErrorCode.RAG_API_ERROR, msg != null ? msg : "Unknown RAGFlow Error");
            }

            // 返回 data 字段，如果 data 不存在则返回整个 map (视具体情况，通常 RAGFlow 返回 code=0, data=...)
            // 兼容性处理：如果 external caller 需要 check code，这里已经 check 过了。
            // 统一返回 wrap 了 code 的 map 还是只返回 data?
            // 根据分析报告，旧逻辑 check code==0 后取 data.
            // 这里我们返回整个 Map，让 Adapter 决定怎么取，或者我们直接在这里剥离？
            // 建议：为了灵活性，返回全量 Map，但在 Client 层做 code!=0 的抛错。
            return map;

        } catch (RenException re) {
            throw re;
        } catch (Exception e) {
            log.error("RAGFlow Client Execute Error! URL: {}, Method: {}, Body Type: {}", url, method,
                    requestEntity.getBody() != null ? requestEntity.getBody().getClass().getName() : "null");
            log.error("Full exception stack trace: ", e);
            throw new RenException(ErrorCode.RAG_API_ERROR, "Request Failed: " + e.getMessage());
        }
    }

    private String buildUrl(String endpoint, Map<String, Object> queryParams) {
        StringBuilder sb = new StringBuilder(baseUrl);
        if (!endpoint.startsWith("/")) {
            sb.append("/");
        }
        sb.append(endpoint);

        if (queryParams != null && !queryParams.isEmpty()) {
            sb.append("?");
            queryParams.forEach((k, v) -> {
                if (v != null) {
                    try {
                        sb.append(k).append("=")
                                .append(java.net.URLEncoder.encode(v.toString(),
                                        StandardCharsets.UTF_8.name()))
                                .append("&");
                    } catch (java.io.UnsupportedEncodingException e) {
                        log.warn("参数编码失败: k={}, v={}", k, v);
                        sb.append(k).append("=").append(v).append("&");
                    }
                }
            });
            // 移除最后一个 &
            sb.setLength(sb.length() - 1);
        }
        return sb.toString();
    }

    /**
     * 发送流式 POST 请求 (SSE)
     * 使用 Java 21 HttpClient 实现
     *
     * @param endpoint API端点
     * @param body     请求体
     * @param onData   数据回调（每收到一行数据调用一次）
     */
    public void postStream(String endpoint, Object body, java.util.function.Consumer<String> onData) {
        try {
            String url = buildUrl(endpoint, null);
            log.debug("POST STREAM {}", url);

            String jsonBody = objectMapper.writeValueAsString(body);

            java.net.http.HttpClient httpClient = java.net.http.HttpClient.newBuilder()
                    .connectTimeout(Duration.ofSeconds(DEFAULT_TIMEOUT))
                    .build();

            java.net.http.HttpRequest request = java.net.http.HttpRequest.newBuilder()
                    .uri(java.net.URI.create(url))
                    .header("Content-Type", "application/json")
                    .header("Authorization", "Bearer " + apiKey)
                    .POST(java.net.http.HttpRequest.BodyPublishers.ofString(jsonBody, StandardCharsets.UTF_8))
                    .build();

            // 发送请求并处理流式响应
            httpClient.send(request, java.net.http.HttpResponse.BodyHandlers.ofInputStream())
                    .body()
                    .transferTo(new java.io.OutputStream() {
                        private final java.io.ByteArrayOutputStream buffer = new java.io.ByteArrayOutputStream();

                        @Override
                        public void write(int b) throws java.io.IOException {
                            if (b == '\n') {
                                String line = buffer.toString(StandardCharsets.UTF_8);
                                if (!line.trim().isEmpty()) {
                                    onData.accept(line);
                                }
                                buffer.reset();
                            } else {
                                buffer.write(b);
                            }
                        }
                    });

        } catch (Exception e) {
            log.error("RAGFlow Stream Request Error", e);
            throw new RenException(ErrorCode.RAG_API_ERROR, "Stream Request Failed: " + e.getMessage());
        }
    }
}
