"""Unified Tool Handler"""

import json
from typing import Dict, List, Any, Optional
from config.logger import setup_logging
from plugins_func.loadplugins import auto_import_modules

from .base import ToolType
from plugins_func.register import Action, ActionResponse
from .unified_tool_manager import ToolManager
from .server_plugins import ServerPluginExecutor
from .server_mcp import ServerMCPExecutor
from .device_iot import DeviceIoTExecutor
from .device_mcp import DeviceMCPExecutor
from .mcp_endpoint import MCPEndpointExecutor


class UnifiedToolHandler:
    """Unified Tool Handler"""

    def __init__(self, conn):
        self.conn = conn
        self.config = conn.config
        self.logger = setup_logging()

        # Create tool manager
        self.tool_manager = ToolManager(conn)

        # Create various executors
        self.server_plugin_executor = ServerPluginExecutor(conn)
        self.server_mcp_executor = ServerMCPExecutor(conn)
        self.device_iot_executor = DeviceIoTExecutor(conn)
        self.device_mcp_executor = DeviceMCPExecutor(conn)
        self.mcp_endpoint_executor = MCPEndpointExecutor(conn)

        # Register executors
        self.tool_manager.register_executor(
            ToolType.SERVER_PLUGIN, self.server_plugin_executor
        )
        self.tool_manager.register_executor(
            ToolType.SERVER_MCP, self.server_mcp_executor
        )
        self.tool_manager.register_executor(
            ToolType.DEVICE_IOT, self.device_iot_executor
        )
        self.tool_manager.register_executor(
            ToolType.DEVICE_MCP, self.device_mcp_executor
        )
        self.tool_manager.register_executor(
            ToolType.MCP_ENDPOINT, self.mcp_endpoint_executor
        )

        # Initialize flag
        self.finish_init = False

    async def _initialize(self):
        """Asynchronous initialization"""
        try:
            # Automatically import plugin modules
            auto_import_modules("plugins_func.functions")

            # Initialize server MCP
            await self.server_mcp_executor.initialize()

            # Initialize MCP endpoint
            await self._initialize_mcp_endpoint()

            # Initialize Home Assistant (if needed)
            self._initialize_home_assistant()

            self.finish_init = True
            self.logger.debug("Unified tool handler init completed")

            # Output the list of currently supported tools
            self.current_support_functions()

        except Exception as e:
            self.logger.error(f"Unified tool handler init failed: {e}")

    async def _initialize_mcp_endpoint(self):
        """Initialize MCP endpoint"""
        try:
            from .mcp_endpoint import connect_mcp_endpoint

            # Get MCP endpoint URL from configuration
            mcp_endpoint_url = self.config.get("mcp_endpoint", "")

            if (
                mcp_endpoint_url
                and "your" not in mcp_endpoint_url
                and mcp_endpoint_url != "null"
            ):
                self.logger.info(f"Initializing MCP endpoint: {mcp_endpoint_url}")
                mcp_endpoint_client = await connect_mcp_endpoint(
                    mcp_endpoint_url, self.conn
                )

                if mcp_endpoint_client:
                    # Save MCP endpoint client to connection object
                    self.conn.mcp_endpoint_client = mcp_endpoint_client
                    self.logger.info("MCP endpoint init success")
                else:
                    self.logger.warning("MCP endpoint init failed")

        except Exception as e:
            self.logger.error(f"Failed to init MCP endpoint: {e}")

    def _initialize_home_assistant(self):
        """Initialize Home Assistant prompt"""
        try:
            from plugins_func.functions.hass_init import append_devices_to_prompt

            append_devices_to_prompt(self.conn)
        except ImportError:
            pass  # Ignore import error
        except Exception as e:
            self.logger.error(f"Failed to init Home Assistant: {e}")

    def get_functions(self) -> List[Dict[str, Any]]:
        """Get function descriptions of all tools"""
        return self.tool_manager.get_function_descriptions()

    def current_support_functions(self) -> List[str]:
        """Get the list of currently supported functions"""
        func_names = self.tool_manager.get_supported_tool_names()
        self.logger.info(f"Currently supported functions: {func_names}")
        return func_names

    def upload_functions_desc(self):
        """Refresh function description list"""
        self.tool_manager.refresh_tools()
        self.logger.info("Function descriptions refreshed")

    def has_tool(self, tool_name: str) -> bool:
        """Check if a specified tool exists"""
        return self.tool_manager.has_tool(tool_name)

    async def handle_llm_function_call(
        self, conn, function_call_data: Dict[str, Any]
    ) -> Optional[ActionResponse]:
        """Handle LLM function call"""
        try:
            # Handle multiple function calls
            if "function_calls" in function_call_data:
                responses = []
                for call in function_call_data["function_calls"]:
                    result = await self.tool_manager.execute_tool(
                        call["name"], call.get("arguments", {})
                    )
                    responses.append(result)
                return self._combine_responses(responses)

            # Handle single function call
            function_name = function_call_data["name"]
            arguments = function_call_data.get("arguments", {})

            # If arguments is a string, try to parse it as JSON
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments) if arguments else {}
                except json.JSONDecodeError:
                    self.logger.error(f"Cannot parse function args: {arguments}")
                    return ActionResponse(
                        action=Action.ERROR,
                        response="Cannot parse function args",
                    )

            self.logger.debug(f"Call function: {function_name}, args: {arguments}")

            # Execute tool call
            result = await self.tool_manager.execute_tool(function_name, arguments)
            return result

        except Exception as e:
            self.logger.error(f"Handle function call error: {e}")
            return ActionResponse(action=Action.ERROR, response=str(e))

    def _combine_responses(self, responses: List[ActionResponse]) -> ActionResponse:
        """Combine responses from multiple function calls"""
        if not responses:
            return ActionResponse(action=Action.NONE, response="No response")

        # If any error, return the first error
        for response in responses:
            if response.action == Action.ERROR:
                return response

        # Combine all successful responses
        contents = []
        responses_text = []

        for response in responses:
            if response.content:
                contents.append(response.content)
            if response.response:
                responses_text.append(response.response)

        # Determine the final action type
        final_action = Action.RESPONSE
        for response in responses:
            if response.action == Action.REQLLM:
                final_action = Action.REQLLM
                break

        return ActionResponse(
            action=final_action,
            result="; ".join(contents) if contents else None,
            response="; ".join(responses_text) if responses_text else None,
        )

    async def register_iot_tools(self, descriptors: List[Dict[str, Any]]):
        """Register IoT device tools"""
        self.device_iot_executor.register_iot_tools(descriptors)
        self.tool_manager.refresh_tools()
        self.logger.info(f"Registered {len(descriptors)} IoT device tools")

    def get_tool_statistics(self) -> Dict[str, int]:
        """Get tool statistics"""
        return self.tool_manager.get_tool_statistics()

    async def cleanup(self):
        """Cleanup resources"""
        try:
            await self.server_mcp_executor.cleanup()

            # Cleanup MCP endpoint connection
            if (
                hasattr(self.conn, "mcp_endpoint_client")
                and self.conn.mcp_endpoint_client
            ):
                await self.conn.mcp_endpoint_client.close()

            self.logger.info("Tool handler cleanup completed")
        except Exception as e:
            self.logger.error(f"Tool handler cleanup failed: {e}")
