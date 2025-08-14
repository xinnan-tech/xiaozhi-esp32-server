"""Server-side MCP tool executor"""

from typing import Dict, Any, Optional

from ..base import ToolType, ToolDefinition, ToolExecutor

from plugins_func.register import Action, ActionResponse

from .mcp_manager import ServerMCPManager

class ServerMCPExecutor(ToolExecutor):
    """Server-side MCP tool executor"""

    def __init__(self, conn):
        self.conn = conn
        self.mcp_manager: Optional[ServerMCPManager] = None
        self._initialized = False

    async def initialize(self):
        """Initialize MCP manager"""
        if not self._initialized:
            self.mcp_manager = ServerMCPManager(self.conn)
            await self.mcp_manager.initialize_servers()
            self._initialized = True

    async def execute(
        self, conn, tool_name: str, arguments: Dict[str, Any]
    ) -> ActionResponse:
        """Execute server-side MCP tool"""
        if not self._initialized or not self.mcp_manager:
            return ActionResponse(
                action=Action.ERROR,
                response="MCP manager not initialized",
            )

        try:
            # Remove mcp_ prefix (if present)
            actual_tool_name = tool_name
            if tool_name.startswith("mcp_"):
                actual_tool_name = tool_name[4:]

            result = await self.mcp_manager.execute_tool(actual_tool_name, arguments)
            return ActionResponse(action=Action.REQLLM, result=str(result))

        except ValueError as e:
            return ActionResponse(
                action=Action.NOTFOUND,
                response=str(e),
            )
        except Exception as e:
            return ActionResponse(
                action=Action.ERROR,
                response=str(e),
            )

    def get_tools(self) -> Dict[str, ToolDefinition]:
        """Get all server-side MCP tools"""
        if not self._initialized or not self.mcp_manager:
            return {}

        tools = {}
        mcp_tools = self.mcp_manager.get_all_tools()

        for tool in mcp_tools:
            func_def = tool.get("function", {})
            tool_name = func_def.get("name", "")
            if tool_name == "":
                continue

            tools[tool_name] = ToolDefinition(
                name=tool_name, description=tool, tool_type=ToolType.SERVER_MCP
            )

        return tools

    def has_tool(self, tool_name: str) -> bool:
        """Check if the specified server-side MCP tool exists"""
        if not self._initialized or not self.mcp_manager:
            return False

        # Remove mcp_ prefix (if present)
        actual_tool_name = tool_name
        if tool_name.startswith("mcp_"):
            actual_tool_name = tool_name[4:]

        return self.mcp_manager.is_mcp_tool(actual_tool_name)

    async def cleanup(self):
        """Clean up MCP connections"""
        if self.mcp_manager:
            await self.mcp_manager.cleanup_all()