"""Server-side Plugin Tool Executor"""

import asyncio
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler
from ..base import ToolType, ToolDefinition, ToolExecutor
from plugins_func.register import all_function_registry, module_func_map, Action, ActionResponse


class ServerPluginExecutor(ToolExecutor):
    """Server-side Plugin Tool Executor"""

    def __init__(self, conn: "ConnectionHandler"):
        self.conn = conn
        self.config = conn.config

    async def execute(
        self, conn: "ConnectionHandler", tool_name: str, arguments: Dict[str, Any]
    ) -> ActionResponse:
        """Execute server-side plugin tool"""
        func_item = all_function_registry.get(tool_name)
        if not func_item:
            return ActionResponse(
                action=Action.NOTFOUND, response=f"Plugin function {tool_name} does not exist"
            )

        try:
            # Determine how to call based on tool type
            if hasattr(func_item, "type"):
                func_type = func_item.type
                if func_type.code in [4, 5]:  # SYSTEM_CTL, IOT_CTL (requires conn parameter)
                    result = func_item.func(conn, **arguments)
                elif func_type.code == 2:  # WAIT
                    result = func_item.func(**arguments)
                elif func_type.code == 3:  # CHANGE_SYS_PROMPT
                    result = func_item.func(conn, **arguments)
                else:
                    result = func_item.func(**arguments)
            else:
                # Default without conn parameter
                result = func_item.func(**arguments)

            # Support async def tool functions
            if asyncio.iscoroutine(result):
                result = await result

            return result

        except Exception as e:
            return ActionResponse(
                action=Action.ERROR,
                response=str(e),
            )

    def _expand_plugin_names(self, config_functions):
        """ expands module-level plugin names to specific function names.

        A single function file may register multiple @register_function,
        If config uses module names (filenames), expand them to specific function name lists.
        """
        if not isinstance(config_functions, list):
            try:
                config_functions = list(config_functions)
            except TypeError:
                return []

        expanded = []
        for name in config_functions:
            if name in module_func_map:
                # Module name, expands to all registered function names in the module
                expanded.extend(module_func_map[name])
            elif name in all_function_registry:
                # Exact match on function name, keep as is
                expanded.append(name)
            else:
                # Unknown name; retaining original value (possibly MCP or other tools)
                expanded.append(name)
        return expanded

    def _get_plugin_description(self, func_name):
        """Get plugin function descriptions, prioritizing exact function name matches, then module name matches."""
        plugins = self.config.get("plugins", {})
        # Exact function name match
        if func_name in plugins:
            return plugins[func_name].get("description", "")
        # Reverse lookup module name via module_func_map
        for module_name, func_names in module_func_map.items():
            if func_name in func_names and module_name in plugins:
                return plugins[module_name].get("description", "")
        return ""

    def get_tools(self) -> Dict[str, ToolDefinition]:
        """Get all registered server-side plugin tools"""
        tools = {}

        # Get necessary functions
        necessary_functions = ["handle_exit_intent", "get_calendar"]

        # Get functions from configuration
        config_functions = self.config["Intent"][
            self.config["selected_module"]["Intent"]
        ].get("functions", [])

        # Convert to list
        if not isinstance(config_functions, list):
            try:
                config_functions = list(config_functions)
            except TypeError:
                config_functions = []

        # Merge all required functions
        all_required_functions = list(set(necessary_functions + config_functions))

        for func_name in all_required_functions:
            func_item = all_function_registry.get(func_name)
            if func_item:
                # Read the description from the function registry.
                fun_description = (
                    self.config.get("plugins", {})
                    .get(func_name, {})
                    .get("description", "")
                )
                if fun_description is not None and len(fun_description) > 0:
                    if "function" in func_item.description and isinstance(
                        func_item.description["function"], dict
                    ):
                        func_item.description["function"][
                            "description"
                        ] = fun_description

                tools[func_name] = ToolDefinition(
                    name=func_name,
                    description=func_item.description,
                    tool_type=ToolType.SERVER_PLUGIN,
                )

        return tools

    def has_tool(self, tool_name: str) -> bool:
        """Check if specified server-side plugin tool exists"""
        return tool_name in all_function_registry
