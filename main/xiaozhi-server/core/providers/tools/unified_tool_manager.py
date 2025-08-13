"""Unified tool manager"""

from typing import Dict, List, Optional, Any

from config.logger import setup_logging

from plugins_func.register import Action, ActionResponse

from .base import ToolType, ToolDefinition, ToolExecutor


class ToolManager:
    """Unified tool manager, manages all types of tools"""

    def __init__(self, conn):
        self.conn = conn
        self.logger = setup_logging()
        self.executors: Dict[ToolType, ToolExecutor] = {}
        self._cached_tools: Optional[Dict[str, ToolDefinition]] = None
        self._cached_function_descriptions: Optional[List[Dict[str, Any]]] = None

    def register_executor(self, tool_type: ToolType, executor: ToolExecutor):
        """Register tool executor"""
        self.executors[tool_type] = executor
        self._invalidate_cache()
        self.logger.info(f"Registered tool executor: {tool_type.value}")

    def _invalidate_cache(self):
        """Invalidate cache"""
        self._cached_tools = None
        self._cached_function_descriptions = None

    def get_all_tools(self) -> Dict[str, ToolDefinition]:
        """Get all tool definitions"""
        if self._cached_tools is not None:
            return self._cached_tools

        all_tools = {}
        for tool_type, executor in self.executors.items():
            try:
                tools = executor.get_tools()
                for name, definition in tools.items():
                    if name in all_tools:
                        self.logger.warning(f"Tool name conflict: {name}")
                    all_tools[name] = definition
            except Exception as e:
                self.logger.error(
                    f"Error getting {tool_type.value} tools: {e}")

        self._cached_tools = all_tools
        return all_tools

    def get_function_descriptions(self) -> List[Dict[str, Any]]:
        """Get function descriptions for all tools (OpenAI format)"""
        if self._cached_function_descriptions is not None:
            return self._cached_function_descriptions

        descriptions = []
        tools = self.get_all_tools()

        for tool_definition in tools.values():
            descriptions.append(tool_definition.description)

        self._cached_function_descriptions = descriptions
        return descriptions

    def has_tool(self, tool_name: str) -> bool:
        """Check if the specified tool exists"""
        tools = self.get_all_tools()
        return tool_name in tools

    def get_tool_type(self, tool_name: str) -> Optional[ToolType]:
        """Get tool type"""
        tools = self.get_all_tools()
        tool_def = tools.get(tool_name)
        return tool_def.tool_type if tool_def else None

    async def execute_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> ActionResponse:
        """Execute tool call"""
        try:
            # Find tool type
            tool_type = self.get_tool_type(tool_name)
            if not tool_type:
                return ActionResponse(
                    action=Action.NOTFOUND,
                    response=f"Tool {tool_name} does not exist",
                )

            # Get corresponding executor
            executor = self.executors.get(tool_type)
            if not executor:
                return ActionResponse(
                    action=Action.ERROR,
                    response=f"Executor for tool type {tool_type.value} is not registered",
                )

            # Execute tool
            self.logger.info(
                f"Executing tool: {tool_name}, arguments: {arguments}")
            result = await executor.execute(self.conn, tool_name, arguments)
            self.logger.debug(f"Tool execution result: {result}")
            return result

        except Exception as e:
            self.logger.error(f"Error executing tool {tool_name}: {e}")
            return ActionResponse(action=Action.ERROR, response=str(e))

    def get_supported_tool_names(self) -> List[str]:
        """Get all supported tool names"""
        tools = self.get_all_tools()
        return list(tools.keys())

    def refresh_tools(self):
        """Refresh tool cache"""
        self._invalidate_cache()
        self.logger.info("Tool cache refreshed")

    def get_tool_statistics(self) -> Dict[str, int]:
        """Get tool statistics"""
        stats = {}
        for tool_type, executor in self.executors.items():
            try:
                tools = executor.get_tools()
                stats[tool_type.value] = len(tools)
            except Exception as e:
                self.logger.error(
                    f"Error getting {tool_type.value} tool statistics: {e}")
                stats[tool_type.value] = 0
        return stats
