"""Server-side MCP client"""

from __future__ import annotations
from datetime import timedelta
import asyncio
import os
import shutil
import concurrent.futures
from contextlib import AsyncExitStack
from typing import Optional, List, Dict, Any
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client
from config.logger import setup_logging
from core.utils.util import sanitize_tool_name

TAG = __name__


class ServerMCPClient:
    """Server-side MCP client for connecting and managing MCP services"""

    def __init__(self, config: Dict[str, Any]):
        """Initialize server-side MCP client

        Args:
            config: MCP service configuration dictionary
        """
        self.logger = setup_logging()
        self.config = config
        self._worker_task: Optional[asyncio.Task] = None
        self._ready_evt = asyncio.Event()
        self._shutdown_evt = asyncio.Event()
        self.session: Optional[ClientSession] = None
        self.tools: List = []  # Original tool objects
        self.tools_dict: Dict[str, Any] = {}
        self.name_mapping: Dict[str, str] = {}

    async def initialize(self):
        """Initialize MCP client connection"""
        if self._worker_task:
            return

        self._worker_task = asyncio.create_task(
            self._worker(), name="ServerMCPClientWorker"
        )

        await self._ready_evt.wait()
        self.logger.bind(tag=TAG).info(
            f"Server-side MCP client connected, available tools: {[name for name in self.name_mapping.values()]}"
        )

    async def cleanup(self):
        """Clean up MCP client resources"""
        if not self._worker_task:
            return

        self._shutdown_evt.set()
        try:
            await asyncio.wait_for(self._worker_task, timeout=20)
        except (asyncio.TimeoutError, Exception) as e:
            self.logger.bind(tag=TAG).error(
                f"Server-side MCP client shutdown error: {e}")
        finally:
            self._worker_task = None

    def has_tool(self, name: str) -> bool:
        """Check if the specified tool is included

        Args:
            name: Tool name

        Returns:
            bool: Whether the tool is included
        """
        return name in self.tools_dict

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get definitions of all available tools

        Returns:
            List[Dict[str, Any]]: Tool definition list
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": tool.description,
                    "parameters": tool.inputSchema,
                },
            }
            for name, tool in self.tools_dict.items()
        ]

    async def call_tool(self, name: str, args: dict) -> Any:
        """Call the specified tool

        Args:
            name: Tool name
            args: Tool parameters

        Returns:
            Any: Tool execution result

        Raises:
            RuntimeError: Thrown when client is not initialized
        """
        if not self.session:
            raise RuntimeError("Server-side MCP client not initialized")

        real_name = self.name_mapping.get(name, name)
        loop = self._worker_task.get_loop()
        coro = self.session.call_tool(real_name, args)

        if loop is asyncio.get_running_loop():
            return await coro

        fut: concurrent.futures.Future = asyncio.run_coroutine_threadsafe(
            coro, loop)
        return await asyncio.wrap_future(fut)

    def is_connected(self) -> bool:
        """Check if MCP client is connected normally

        Returns:
            bool: Returns True if client is connected and working normally, otherwise False
        """
        # Check if worker task exists
        if self._worker_task is None:
            return False

        # Check if worker task is completed or cancelled
        if self._worker_task.done():
            return False

        # Check if session exists
        if self.session is None:
            return False

        # All checks passed, connection is normal
        return True

    async def _worker(self):
        """MCP client worker coroutine"""
        async with AsyncExitStack() as stack:
            try:
                # Establish StdioClient
                if "command" in self.config:
                    cmd = (
                        shutil.which("npx")
                        if self.config["command"] == "npx"
                        else self.config["command"]
                    )
                    env = {**os.environ, **self.config.get("env", {})}
                    params = StdioServerParameters(
                        command=cmd,
                        args=self.config.get("args", []),
                        env=env,
                    )
                    stdio_r, stdio_w = await stack.enter_async_context(
                        stdio_client(params)
                    )
                    read_stream, write_stream = stdio_r, stdio_w

                # Establish SSEClient
                elif "url" in self.config:
                    if "API_ACCESS_TOKEN" in self.config:
                        headers = {
                            "Authorization": f"Bearer {self.config['API_ACCESS_TOKEN']}"
                        }
                    else:
                        headers = {}

                    sse_r, sse_w = await stack.enter_async_context(
                        sse_client(self.config["url"], headers=headers)
                    )
                    read_stream, write_stream = sse_r, sse_w

                else:
                    raise ValueError(
                        "MCP client configuration must contain 'command' or 'url'")

                self.session = await stack.enter_async_context(
                    ClientSession(
                        read_stream=read_stream,
                        write_stream=write_stream,
                        read_timeout_seconds=timedelta(seconds=15),
                    )
                )

                await self.session.initialize()

                # Get tools
                self.tools = (await self.session.list_tools()).tools

                for t in self.tools:
                    sanitized = sanitize_tool_name(t.name)
                    self.tools_dict[sanitized] = t
                    self.name_mapping[sanitized] = t.name

                self._ready_evt.set()

                # Suspend and wait for shutdown
                await self._shutdown_evt.wait()

            except Exception as e:
                self.logger.bind(tag=TAG).error(
                    f"Server-side MCP client worker coroutine error: {e}")
                self._ready_evt.set()
                raise
