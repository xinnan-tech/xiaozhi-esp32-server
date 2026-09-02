"""Server MCP manager"""

import asyncio
import os
import json
from typing import Dict, Any, List

from mcp.types import LoggingMessageNotificationParams

from config.config_loader import get_project_dir
from config.logger import setup_logging
from .mcp_client import ServerMCPClient

TAG = __name__
logger = setup_logging()


class ServerMCPManager:
    """Manage multiple server MCP services"""

    def __init__(self, conn) -> None:
        """Initialize MCP manager"""
        self.conn = conn
        self.config_path = get_project_dir() + "data/.mcp_server_settings.json"
        if not os.path.exists(self.config_path):
            self.config_path = ""
            logger.bind(tag=TAG).warning(
                f"MCP server config file not found: {self.config_path}"
            )
        self.clients: Dict[str, ServerMCPClient] = {}
        self.tools = []
        self._init_lock = asyncio.Lock()

    def load_config(self) -> Dict[str, Any]:
        """Load MCP server config"""
        if len(self.config_path) == 0:
            return {}

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            return config.get("mcpServers", {})
        except Exception as e:
            logger.bind(tag=TAG).error(
                f"Error loading MCP config from {self.config_path}: {e}"
            )
            return {}

    async def _init_server(self, name: str, srv_config: Dict[str, Any]):
        """Initialize single MCP server"""
        client = None
        try:
            # Initialize server MCP client
            logger.bind(tag=TAG).info(f"Initialize server MCP client: {name}")
            client = ServerMCPClient(srv_config)
            # Set timeout to 10 seconds
            await asyncio.wait_for(client.initialize(logging_callback=self.logging_callback), timeout=10)

            # Use lock to protect shared state modification
            async with self._init_lock:
                self.clients[name] = client
                client_tools = client.get_available_tools()
                self.tools.extend(client_tools)

        except asyncio.TimeoutError:
            logger.bind(tag=TAG).error(
                f"Failed to initialize MCP server {name}: Timeout"
            )
            if client:
                await client.cleanup()
        except Exception as e:
            logger.bind(tag=TAG).error(
                f"Failed to initialize MCP server {name}: {e}"
            )
            if client:
                await client.cleanup()

    async def initialize_servers(self) -> None:
        """Initialize all MCP servers"""
        config = self.load_config()
        tasks = []
        for name, srv_config in config.items():
            if not srv_config.get("command") and not srv_config.get("url"):
                logger.bind(tag=TAG).warning(
                    f"Skipping server {name}: neither command nor url specified"
                )
                continue
            
            tasks.append(self._init_server(name, srv_config))
        
        if tasks:
            await asyncio.gather(*tasks)

        # Output the list of supported server MCP tools
        if hasattr(self.conn, "func_handler") and self.conn.func_handler:
            # Refresh tool cache to ensure server MCP tools are correctly loaded
            if hasattr(self.conn.func_handler, "tool_manager"):
                self.conn.func_handler.tool_manager.refresh_tools()
            self.conn.func_handler.current_support_functions()

    def get_all_tools(self) -> List[Dict[str, Any]]:
        """Get all tools function definitions"""
        return self.tools

    def is_mcp_tool(self, tool_name: str) -> bool:
        """Check if it is an MCP tool"""
        for tool in self.tools:
            if (
                tool.get("function") is not None
                and tool["function"].get("name") == tool_name
            ):
                return True
        return False

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute tool call, retry when failed"""
        logger.bind(tag=TAG).info(f"Execute server MCP tool {tool_name}, arguments: {arguments}")

        max_retries = 3  # Maximum retry times
        retry_interval = 2  # Retry interval (seconds)

        # Find the corresponding client
        client_name = None
        target_client = None
        for name, client in self.clients.items():
            if client.has_tool(tool_name):
                client_name = name
                target_client = client
                break

        if not target_client:
            raise ValueError(f"Tool {tool_name} not found in any MCP server")

        # Tool call with retry mechanism
        for attempt in range(max_retries):
            try:
                return await target_client.call_tool(tool_name, arguments, progress_callback=self.progress_callback)
            except Exception as e:
                # If the last attempt fails, throw the exception directly
                if attempt == max_retries - 1:
                    raise

                logger.bind(tag=TAG).warning(
                    f"Failed to execute tool {tool_name} (attempt {attempt+1}/{max_retries}): {e}"
                )

                # Try to reconnect before retry
                logger.bind(tag=TAG).info(
                    f"Before retry, try to reconnect MCP client {client_name}"
                )
                try:
                    # Close the old connection
                    await target_client.cleanup()

                    # Reinitialize the client
                    config = self.load_config()
                    if client_name in config:
                        client = ServerMCPClient(config[client_name])
                        await client.initialize(logging_callback=self.logging_callback)
                        self.clients[client_name] = client
                        target_client = client
                        logger.bind(tag=TAG).info(
                            f"Successfully reconnected MCP client: {client_name}"
                        )
                    else:
                        logger.bind(tag=TAG).error(
                            f"Cannot reconnect MCP client {client_name}: config not found"
                        )
                except Exception as reconnect_error:
                    logger.bind(tag=TAG).error(
                        f"Failed to reconnect MCP client {client_name}: {reconnect_error}"
                    )

                # Wait for a while before retrying
                await asyncio.sleep(retry_interval)

    async def cleanup_all(self) -> None:
        """Close all MCP clients"""
        for name, client in list(self.clients.items()):
            try:
                if hasattr(client, "cleanup"):
                    await asyncio.wait_for(client.cleanup(), timeout=20)
                logger.bind(tag=TAG).info(f"Server MCP client closed: {name}")
            except (asyncio.TimeoutError, Exception) as e:
                logger.bind(tag=TAG).error(f"Failed to close MCP client {name}: {e}")
        self.clients.clear()

    # Optional callback methods

    async def logging_callback(self, params: LoggingMessageNotificationParams):
        logger.bind(tag=TAG).info(f"[Server Log - {params.level.upper()}] {params.data}")

    async def progress_callback(self, progress: float, total: float | None, message: str | None) -> None:
        logger.bind(tag=TAG).info(f"[Progress {progress}/{total}]: {message}")