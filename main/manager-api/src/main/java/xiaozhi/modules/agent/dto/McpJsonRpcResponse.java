package xiaozhi.modules.agent.dto;

import lombok.Data;

/**
 * MCP JSON-RPC 响应 DTO
 */
@Data
public class McpJsonRpcResponse {
    private String jsonrpc = "2.0";
    private Integer id;
    private McpResult result;
    private McpError error;

    public McpJsonRpcResponse() {
    }

    @Data
    public static class McpResult {
        private String type;
        private String message;
        private String agent_id;
        private McpTool[] tools;

        public McpResult() {
        }
    }

    @Data
    public static class McpTool {
        private String name;
        private String description;
        private Object inputSchema;

        public McpTool() {
        }
    }

    @Data
    public static class McpError {
        private Integer code;
        private String message;
        private Object data;

        public McpError() {
        }
    }
}