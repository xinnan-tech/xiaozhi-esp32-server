from datetime import timedelta
from typing import Optional
from contextlib import AsyncExitStack
import os, shutil
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from config.logger import setup_logging

TAG = __name__

class MCPClient:
    def __init__(self, config):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.logger = setup_logging()
        self.config = config
        self.tolls = []

    async def initialize(self):
        args = self.config.get("args", [])

        command = (
            shutil.which("npx")
            if self.config["command"] == "npx"
            else self.config["command"]
        )
        
        env={**os.environ}
        if self.config.get("env"):
            env.update(self.config["env"])
        
        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=env
        )
        
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        time_out_delta =  timedelta(seconds=15)
        self.session = await self.exit_stack.enter_async_context(ClientSession(read_stream=self.stdio, write_stream=self.write, read_timeout_seconds=time_out_delta))
        
        await self.session.initialize()
        
        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        self.tools = tools
        self.logger.bind(tag=TAG).info(f"Connected to server with tools:{[tool.name for tool in tools]}")
    
    def has_tool(self, tool_name):
        return any(tool.name == tool_name for tool in self.tools)
    
    def get_available_tools(self):
        available_tools = [{"type": "function", "function":{ 
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.inputSchema
        } } for tool in self.tools]

        return available_tools
    
    async def call_tool(self, tool_name: str, tool_args: dict):
        self.logger.bind(tag=TAG).info(f"MCPClient Calling tool {tool_name} with args: {tool_args}")
        try:
            response = await self.session.call_tool(tool_name, tool_args)
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Error calling tool {tool_name}: {e}")
            from types import SimpleNamespace
            error_content = SimpleNamespace(
                type='text',
                text=f"Error calling tool {tool_name}: {e}"
            )
            error_response = SimpleNamespace(
                content=[error_content],
                isError=True
            )
            return error_response
        self.logger.bind(tag=TAG).info(f"MCPClient Response from tool {tool_name}: {response}")
        return response

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()