from __future__ import annotations

from datetime import timedelta
import asyncio, os, shutil, concurrent.futures
from contextlib import AsyncExitStack
from typing import Optional, List, Dict, Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client
from config.logger import setup_logging

TAG = __name__


class MCPClient:
    def __init__(self, config: Dict[str, Any]):
        self.logger = setup_logging()
        self.config = config

        self._worker_task: Optional[asyncio.Task] = None
        self._ready_evt = asyncio.Event()
        self._shutdown_evt = asyncio.Event()

        self.session: Optional[ClientSession] = None
        self.tools: List = []

    async def initialize(self):
        if self._worker_task:
            return
        self._worker_task = asyncio.create_task(self._worker(), name="MCPClientWorker")
        await self._ready_evt.wait()

        self.logger.bind(tag=TAG).info(
            f"Connected, tools = {[t.name for t in self.tools]}"
        )

    async def cleanup(self):
        if not self._worker_task:
            return

        self._shutdown_evt.set()
        try:
            await asyncio.wait_for(self._worker_task, timeout=20)
        except (asyncio.TimeoutError, Exception) as e:
            self.logger.bind(tag=TAG).error(f"worker shutdown err: {e}")
        finally:
            self._worker_task = None

    def has_tool(self, name: str) -> bool:
        return any(t.name == name for t in self.tools)

    def get_available_tools(self):
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.inputSchema,
                },
            }
            for t in self.tools
        ]

    async def call_tool(self, name: str, args: dict):
        if not self.session:
            raise RuntimeError("MCPClient not initialized")

        loop = self._worker_task.get_loop()
        coro = self.session.call_tool(name, args)

        if loop is asyncio.get_running_loop():
            return await coro

        fut: concurrent.futures.Future = asyncio.run_coroutine_threadsafe(coro, loop)
        return await asyncio.wrap_future(fut)

    async def _worker(self):
        async with AsyncExitStack() as stack:
            try:
                # 建立 StdioClient
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
                    stdio_r, stdio_w = await stack.enter_async_context(stdio_client(params))
                    read_stream, write_stream = stdio_r, stdio_w
                # 建立SSEClient
                elif "url" in self.config:
                    sse_r, sse_w = await stack.enter_async_context(sse_client(self.config["url"]))
                    read_stream, write_stream = sse_r, sse_w

                else:
                    raise ValueError("MCPClient config must include 'command' or 'url'")

                self.session = await stack.enter_async_context(
                    ClientSession(
                        read_stream=read_stream,
                        write_stream=write_stream,
                        read_timeout_seconds=timedelta(seconds=15),
                    )
                )
                await self.session.initialize()

                # 获取工具
                self.tools = (await self.session.list_tools()).tools

                self._ready_evt.set()

                # 挂起等待关闭
                await self._shutdown_evt.wait()

            except Exception as e:
                self.logger.bind(tag=TAG).error(f"worker error: {e}")
                self._ready_evt.set()
                raise
