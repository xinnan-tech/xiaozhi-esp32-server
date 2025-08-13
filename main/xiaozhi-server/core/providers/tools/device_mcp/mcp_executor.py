"""Device-side MCP tool executor"""

from typing import Dict, Any
from ..base import ToolType, ToolDefinition, ToolExecutor
from plugins_func.register import Action, ActionResponse
from .mcp_handler import call_mcp_tool

class DeviceMCPExecutor(ToolExecutor):
    """Device-side MCP tool executor"""
    
    def __init__(self, conn):
        self.conn = conn

    async def execute(
        self, conn, tool_name: str, arguments: Dict[str, Any]
    ) -> ActionResponse:
        """Execute device-side MCP tool"""
        if not hasattr(conn, "mcp_client") or not conn.mcp_client:
            return ActionResponse(
                action=Action.ERROR,
                response="Device-side MCP client not initialized",
            )

        if not await conn.mcp_client.is_ready():
            return ActionResponse(
                action=Action.ERROR,
                response="Device-side MCP client not ready",
            )

        try:
            # Convert parameters to JSON string
            import json
            args_str = json.dumps(arguments) if arguments else "{}"
            
            # Call device-side MCP tool
            result = await call_mcp_tool(conn, conn.mcp_client, tool_name, args_str)
            
            resultJson = None
            if isinstance(result, str):
                try:
                    resultJson = json.loads(result)
                except Exception as e:
                    pass

            # Vision models do not go through secondary LLM processing
            if (
                resultJson is not None
                and isinstance(resultJson, dict)
                and "action" in resultJson
            ):
                return ActionResponse(
                    action=Action[resultJson["action"]],
                    response=resultJson.get("response", ""),
                )

            return ActionResponse(action=Action.REQLLM, result=str(result))

        except ValueError as e:
            return ActionResponse(action=Action.NOTFOUND, response=str(e))
        except Exception as e:
            return ActionResponse(action=Action.ERROR, response=str(e))

    def get_tools(self) -> Dict[str, ToolDefinition]:
        """Get all device-side MCP tools"""
        if not hasattr(self.conn, "mcp_client") or not self.conn.mcp_client:
            return {}

        tools = {}
        mcp_tools = self.conn.mcp_client.get_available_tools()
        
        for tool in mcp_tools:
            func_def = tool.get("function", {})
            tool_name = func_def.get("name", "")
            if tool_name:
                tools[tool_name] = ToolDefinition(
                    name=tool_name, description=tool, tool_type=ToolType.DEVICE_MCP
                )

        return tools

    def has_tool(self, tool_name: str) -> bool:
        """Check if the specified device-side MCP tool exists"""
        if not hasattr(self.conn, "mcp_client") or not self.conn.mcp_client:
            return False
        return self.conn.mcp_client.has_tool(tool_name)