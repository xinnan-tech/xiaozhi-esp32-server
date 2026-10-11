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

import cn.hutool.crypto.digest.DigestUtil;
import lombok.AllArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import xiaozhi.common.constant.Constant;
import xiaozhi.common.utils.AESUtils;
import xiaozhi.common.utils.JsonUtils;
import xiaozhi.modules.agent.Enums.XiaoZhiMcpJsonRpcJson;
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
        // Get MCP address
        String url = sysParamsService.getValue(Constant.SERVER_MCP_ENDPOINT, true);
        if (StringUtils.isBlank(url) || "null".equals(url)) {
            return null;
        }
        URI uri = getURI(url);
        // Get agent MCP URL prefix
        String agentMcpUrl = getAgentMcpUrl(uri);
        // Get secret key
        String key = getSecretKey(uri);
        // Get encrypted token
        String encryptToken = encryptToken(id, key);
        // URL encode the token
        String encodedToken = URLEncoder.encode(encryptToken, StandardCharsets.UTF_8);
        // Return agent MCP path format
        agentMcpUrl = "%s/mcp/?token=%s".formatted(agentMcpUrl, encodedToken);
        return agentMcpUrl;
    }

    @Override
    public List<String> getAgentMcpToolsList(String id) {
        String wsUrl = getAgentMcpAccessAddress(id);
        if (StringUtils.isBlank(wsUrl)) {
            return List.of();
        }

        // Replace /mcp with /call
        wsUrl = wsUrl.replace("/mcp/", "/call/");

        try {
            // Create WebSocket connection, increase timeout to 15 seconds
            try (WebSocketClientManager client = WebSocketClientManager.build(
                    new WebSocketClientManager.Builder()
                            .uri(wsUrl)
                            .bufferSize(1024 * 1024)
                            .connectTimeout(8, TimeUnit.SECONDS)
                            .maxSessionDuration(10, TimeUnit.SECONDS))) {

                // Step 1: Send initialization message and wait for response
                log.info("Sending MCP initialization message, Agent ID: {}", id);
                client.sendText(XiaoZhiMcpJsonRpcJson.getInitializeJson());

                // Wait for initialization response (id=1) - Remove fixed delay, change to response-driven
                List<String> initResponses = client.listenerWithoutClose(response -> {
                    try {
                        Map<String, Object> jsonMap = JsonUtils.parseMap(response);
                        if (jsonMap != null && Integer.valueOf(1).equals(jsonMap.get("id"))) {
                            // Check if there is a result field, indicating successful initialization
                            return jsonMap.containsKey("result") && !jsonMap.containsKey("error");
                        }
                        return false;
                    } catch (Exception e) {
                        log.warn("Failed to parse initialization response: {}", response, e);
                        return false;
                    }
                });

                // Validate initialization response
                boolean initSucceeded = false;
                for (String response : initResponses) {
                    try {
                        Map<String, Object> jsonMap = JsonUtils.parseMap(response);
                        if (jsonMap != null && Integer.valueOf(1).equals(jsonMap.get("id"))) {
                            if (jsonMap.containsKey("result")) {
                                log.info("MCP initialization successful, Agent ID: {}", id);
                                initSucceeded = true;
                                break;
                            } else if (jsonMap.containsKey("error")) {
                                log.error("MCP initialization failed, Agent ID: {}, Error: {}", id, jsonMap.get("error"));
                                return List.of();
                            }
                        }
                    } catch (Exception e) {
                        log.warn("Failed to process initialization response: {}", response, e);
                    }
                }

                if (!initSucceeded) {
                    log.error("No valid MCP initialization response received, Agent ID: {}", id);
                    return List.of();
                }

                // Step 2: Send initialization complete notification - only send after receiving initialize response
                log.info("Sending MCP initialization complete notification, Agent ID: {}", id);
                client.sendText(XiaoZhiMcpJsonRpcJson.getNotificationsInitializedJson());
                // Step 3: Send tools list request - send immediately, no additional delay needed
                log.info("Sending MCP tools list request, Agent ID: {}", id);
                client.sendText(XiaoZhiMcpJsonRpcJson.getToolsListJson());

                // Wait for tools list response (id=2)
                List<String> toolsResponses = client.listener(response -> {
                    try {
                        Map<String, Object> jsonMap = JsonUtils.parseMap(response);
                        return jsonMap != null && Integer.valueOf(2).equals(jsonMap.get("id"));
                    } catch (Exception e) {
                        log.warn("Failed to parse tools list response: {}", response, e);
                        return false;
                    }
                });

                // Process tools list response
                for (String response : toolsResponses) {
                    try {
                        Map<String, Object> jsonMap = JsonUtils.parseMap(response);
                        if (jsonMap != null && Integer.valueOf(2).equals(jsonMap.get("id"))) {
                            // Check if there is a result field
                            Object resultObj = jsonMap.get("result");
                            if (resultObj instanceof Map<?, ?>) {
                                Map<String, Object> resultMap = JsonUtils.toStringObjectMap(resultObj);
                                Object toolsObj = resultMap.get("tools");
                                if (toolsObj instanceof List) {
                                    List<Map<String, Object>> toolsList = (List<Map<String, Object>>) toolsObj;
                                    // Extract tool name list
                                    List<String> result = toolsList.stream()
                                            .map(tool -> String.class.cast(tool.get("name")))
                                            .filter(name -> name != null)
                                            .sorted()
                                            .collect(Collectors.toList());
                                    log.info("Successfully obtained MCP tools list, Agent ID: {}, Tool count: {}", id, result.size());
                                    return result;
                                }
                            } else if (jsonMap.containsKey("error")) {
                                log.error("Failed to get tools list, Agent ID: {}, Error: {}", id, jsonMap.get("error"));
                                return List.of();
                            }
                        }
                    } catch (Exception e) {
                        log.warn("Failed to process tools list response: {}", response, e);
                    }
                }

                log.warn("No valid tools list response found, Agent ID: {}", id);
                return List.of();

            }
        } catch (Exception e) {
            log.error("Failed to get agent MCP tools list, Agent ID: {}, Error reason: {}", id, e.getMessage());
            return List.of();
        }
    }

    /**
     * Get URI object
     * 
     * @param url path
     * @return URI object
     */
    private static URI getURI(String url) {
        try {
            return new URI(url);
        } catch (URISyntaxException e) {
            log.error("Incorrect path format: {}, \nError message: {}", url, e.getMessage());
            throw new RuntimeException("MCP address has errors, please go to parameter management to modify MCP access point address");
        }
    }

    /**
     * Get secret key
     *
     * @param uri MCP address
     * @return secret key
     */
    private static String getSecretKey(URI uri) {
        // Get parameters
        String query = uri.getQuery();
        // Get AES encryption key
        String str = "key=";
        return query.substring(query.indexOf(str) + str.length());
    }

    /**
     * Get agent MCP access point URL
     *
     * @param uri MCP address
     * @return Agent MCP access point URL
     */
    private String getAgentMcpUrl(URI uri) {
        // Get protocol
        String wsScheme = (uri.getScheme().equals("https")) ? "wss" : "ws";
        // Get host, port, path
        String path = uri.getSchemeSpecificPart();
        // Get path before the last /
        path = path.substring(0, path.lastIndexOf("/"));
        return wsScheme + ":" + path;
    }

    /**
     * Get encrypted token for agent ID
     *
     * @param agentId Agent ID
     * @param key     Encryption key
     * @return Encrypted token
     */
    private static String encryptToken(String agentId, String key) {
        // Use MD5 to encrypt agent ID
        String md5 = HashEncryptionUtil.Md5hexDigest(agentId);
        // AES needs encrypted text
        String json = "{\"agentId\": \"%s\"}".formatted(md5);
        // Encrypt to token value
        return AESUtils.encrypt(key, json);
    }
}
