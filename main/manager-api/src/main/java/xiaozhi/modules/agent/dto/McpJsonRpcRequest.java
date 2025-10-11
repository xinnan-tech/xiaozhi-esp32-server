package xiaozhi.modules.agent.dto;

import lombok.Data;

/**
 * MCP JSON-RPC 请求 DTO
 */
@Data
public class McpJsonRpcRequest {
    private String jsonrpc = "2.0";
    private String method;
    private Object params;
    private Integer id;

    public McpJsonRpcRequest() {
    }

    public McpJsonRpcRequest(String method) {
        this.method = method;
    }

    public McpJsonRpcRequest(String method, Object params, Integer id) {
        this.method = method;
        this.params = params;
        this.id = id;
    }

    public McpJsonRpcRequest(String method, Object params) {
        this.method = method;
        this.params = params;
    }
}