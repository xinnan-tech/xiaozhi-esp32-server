package xiaozhi.modules.agent.service.impl;

import java.net.URI;
import java.net.URISyntaxException;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Service;

import lombok.AllArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import xiaozhi.common.constant.Constant;
import xiaozhi.common.utils.AESUtils;
import xiaozhi.common.utils.HashEncryptionUtil;
import xiaozhi.common.utils.JsonUtils;
import xiaozhi.modules.agent.dto.McpJsonRpcRequest;
import xiaozhi.modules.agent.service.AgentMcpAccessPointService;
import xiaozhi.modules.sys.service.SysParamsService;
import xiaozhi.modules.sys.utils.WebSocketClientManager;

@AllArgsConstructor
@Service
@Slf4j
public class AgentMcpAccessPointServiceImpl implements AgentMcpAccessPointService {
    private SysParamsService sysParamsService;

    @Override
    public String getAgentMcpAccessAddress(String id) {
        // 获取到mcp的地址
        String url = sysParamsService.getValue(Constant.SERVER_MCP_ENDPOINT, true);
        if (StringUtils.isBlank(url) || "null".equals(url)) {
            return null;
        }
        URI uri = getURI(url);
        // 获取智能体mcp的url前缀
        String agentMcpUrl = getAgentMcpUrl(uri);
        // 获取密钥
        String key = getSecretKey(uri);
        // 获取加密的token
        String encryptToken = encryptToken(id, key);
        // 对token进行URL编码
        String encodedToken = URLEncoder.encode(encryptToken, StandardCharsets.UTF_8);
        // 返回智能体Mcp路径的格式
        agentMcpUrl = "%s/mcp/?token=%s".formatted(agentMcpUrl, encodedToken);
        return agentMcpUrl;
    }

    @Override
    public List<String> getAgentMcpToolsList(String id) {
        String wsUrl = getAgentMcpAccessAddress(id);
        if (StringUtils.isBlank(wsUrl)) {
            return List.of();
        }

        // 将 /mcp 替换为 /call
        wsUrl = wsUrl.replace("/mcp/", "/call/");

        try {
            // 创建 WebSocket 连接
            try (WebSocketClientManager client = WebSocketClientManager.build(
                    new WebSocketClientManager.Builder()
                            .uri(wsUrl)
                            .connectTimeout(5, TimeUnit.SECONDS)
                            .maxSessionDuration(9, TimeUnit.SECONDS))) {

                // 发送初始化消息
                McpJsonRpcRequest initializeRequest = new McpJsonRpcRequest("initialize",
                        Map.of(
                                "protocolVersion", "2024-11-05",
                                "capabilities", Map.of(
                                        "roots", Map.of("listChanged", false),
                                        "sampling", Map.of()),
                                "clientInfo", Map.of(
                                        "name", "xz-mcp-broker",
                                        "version", "0.0.1")),
                        1);
                client.sendJson(initializeRequest);

                // 等待初始化响应
                Thread.sleep(200);

                // 发送初始化完成通知
                // 对于通知类型的消息，手动构建JSON以避免包含null字段
                String notificationJson = "{\"jsonrpc\":\"2.0\",\"method\":\"notifications/initialized\"}";
                client.sendText(notificationJson);

                // 等待 0.2 秒
                Thread.sleep(200);

                // 发送工具列表请求
                McpJsonRpcRequest toolsRequest = new McpJsonRpcRequest("tools/list", null, 2);
                client.sendJson(toolsRequest);

                // 监听响应，直到收到包含 id=2 的响应（tools/list响应）
                List<String> responses = client.listener(response -> {
                    try {
                        // 先尝试解析为通用JSON对象来获取id
                        Map<String, Object> jsonMap = JsonUtils.parseObject(response, Map.class);
                        return jsonMap != null && Integer.valueOf(2).equals(jsonMap.get("id"));
                    } catch (Exception e) {
                        log.warn("解析响应失败: {}", response, e);
                        return false;
                    }
                });

                // 处理响应
                for (String response : responses) {
                    try {
                        // 先解析为通用JSON对象
                        Map<String, Object> jsonMap = JsonUtils.parseObject(response, Map.class);
                        if (jsonMap != null && Integer.valueOf(2).equals(jsonMap.get("id"))) {
                            // 检查是否有result字段
                            Object resultObj = jsonMap.get("result");
                            if (resultObj instanceof Map) {
                                Map<String, Object> resultMap = (Map<String, Object>) resultObj;
                                Object toolsObj = resultMap.get("tools");
                                if (toolsObj instanceof List) {
                                    List<Map<String, Object>> toolsList = (List<Map<String, Object>>) toolsObj;
                                    // 提取工具名称列表
                                    return toolsList.stream()
                                            .map(tool -> (String) tool.get("name"))
                                            .filter(name -> name != null)
                                            .collect(Collectors.toList());
                                }
                            }
                        }
                    } catch (Exception e) {
                        log.warn("处理工具列表响应失败: {}", response, e);
                    }
                }

                log.warn("未找到有效的工具列表响应");
                return List.of();

            }
        } catch (Exception e) {
            log.error("获取智能体 MCP 工具列表失败，智能体ID: {}", id, e);
            return List.of();
        }
    }

    /**
     * 获取URI对象
     * 
     * @param url 路径
     * @return URI对象
     */
    private static URI getURI(String url) {
        try {
            return new URI(url);
        } catch (URISyntaxException e) {
            log.error("路径格式不正确路径：{}，\n错误信息:{}", url, e.getMessage());
            throw new RuntimeException("mcp的地址存在错误，请进入参数管理修改mcp接入点地址");
        }
    }

    /**
     * 获取密钥
     *
     * @param uri mcp地址
     * @return 密钥
     */
    private static String getSecretKey(URI uri) {
        // 获取参数
        String query = uri.getQuery();
        // 获取aes加密密钥
        String str = "key=";
        return query.substring(query.indexOf(str) + str.length());
    }

    /**
     * 获取智能体mcp接入点url
     *
     * @param uri mcp地址
     * @return 智能体mcp接入点url
     */
    private String getAgentMcpUrl(URI uri) {
        // 获取协议
        String wsScheme = (uri.getScheme().equals("https")) ? "wss" : "ws";
        // 获取主机，端口，路径
        String path = uri.getSchemeSpecificPart();
        // 获取到最后一个/前的path
        path = path.substring(0, path.lastIndexOf("/"));
        return wsScheme + ":" + path;
    }

    /**
     * 获取对智能体id加密的token
     *
     * @param agentId 智能体id
     * @param key     加密密钥
     * @return 加密后token
     */
    private static String encryptToken(String agentId, String key) {
        // 使用md5对智能体id进行加密
        String md5 = HashEncryptionUtil.Md5hexDigest(agentId);
        // aes需要加密文本
        String json = "{\"agentId\": \"%s\"}".formatted(md5);
        // 加密后成token值
        return AESUtils.encrypt(key, json);
    }
}
