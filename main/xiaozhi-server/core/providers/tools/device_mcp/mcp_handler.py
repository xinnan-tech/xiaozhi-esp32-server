"""Device-side MCP Client Support Module"""

import json
import asyncio
import re
import re
from datetime import datetime
from concurrent.futures import Future
from core.utils.util import get_vision_url, sanitize_tool_name
from core.utils.auth import AuthToken
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


class MCPClient:
    """Device-side MCP Client for managing state and tools"""

    def __init__(self):
        self.tools = {}  # sanitized_name -> tool_data
        self.name_mapping = {}
        self.ready = False
        self.call_results = {}  # To store Futures for tool call responses
        self.next_id = 1
        self.lock = asyncio.Lock()
        self._cached_available_tools = None  # Cache for get_available_tools

    def has_tool(self, name: str) -> bool:
        return name in self.tools

    def get_available_tools(self) -> list:
        if self._cached_available_tools is not None:
            return self._cached_available_tools

        result = []
        for tool_name, tool_data in self.tools.items():
            function_def = {
                "name": tool_name,
                "description": tool_data["description"],
                "parameters": {
                    "type": tool_data["inputSchema"].get("type", "object"),
                    "properties": tool_data["inputSchema"].get("properties", {}),
                    "required": tool_data["inputSchema"].get("required", []),
                },
            }
            result.append({"type": "function", "function": function_def})

        self._cached_available_tools = result
        return result

    async def is_ready(self) -> bool:
        async with self.lock:
            return self.ready

    async def set_ready(self, status: bool):
        async with self.lock:
            self.ready = status

    async def add_tool(self, tool_data: dict):
        async with self.lock:
            sanitized_name = sanitize_tool_name(tool_data["name"])
            self.tools[sanitized_name] = tool_data
            self.name_mapping[sanitized_name] = tool_data["name"]
            logger.bind(tag=TAG).debug(f"Registered MCP tool: {sanitized_name} (original: {tool_data['name']})")
            self._cached_available_tools = None  # Invalidate cache

    async def get_next_id(self) -> int:
        async with self.lock:
            current_id = self.next_id
            self.next_id += 1
            return current_id

    async def register_call_result_future(self, id: int, future: Future):
        async with self.lock:
            self.call_results[id] = future

    async def resolve_call_result(self, id: int, result: any):
        async with self.lock:
            if id in self.call_results:
                future = self.call_results.pop(id)
                if not future.done():
                    future.set_result(result)

    async def reject_call_result(self, id: int, exception: Exception):
        async with self.lock:
            if id in self.call_results:
                future = self.call_results.pop(id)
                if not future.done():
                    future.set_exception(exception)

    async def cleanup_call_result(self, id: int):
        async with self.lock:
            if id in self.call_results:
                self.call_results.pop(id)


async def _background_tool_refresh(conn):
    """Refreshes LLM tools in a separate thread to prevent blocking the network"""
    try:
        # Offload synchronous work to threads
        await asyncio.to_thread(conn.func_handler.tool_manager.refresh_tools)
        await asyncio.to_thread(conn.func_handler.current_support_functions)
        logger.bind(tag=TAG).info("LLM tool definitions refreshed in background.")
    except Exception as e:
        logger.bind(tag=TAG).error(f"Background tool refresh failed: {e}")


async def send_mcp_message(conn, payload: dict):
    """Helper to send MCP messages"""
    if not conn.features.get("mcp"):
        logger.bind(tag=TAG).warning("Client does not support MCP, skipping message")
        return

    message = json.dumps({"type": "mcp", "payload": payload})

    try:
        await conn.websocket.send(message)
        logger.bind(tag=TAG).debug(f"MCP message sent: {payload.get('method', 'response')}")
    except Exception as e:
        logger.bind(tag=TAG).error(f"Failed to send MCP message: {e}")


async def handle_mcp_message(conn, mcp_client: MCPClient, payload: dict):
    """Process incoming MCP messages"""
    logger.bind(tag=TAG).debug("Processing incoming MCP payload...")

    if not isinstance(payload, dict):
        logger.bind(tag=TAG).error("MCP message missing payload or has invalid format")
        return

    # Handle result payloads
    if "result" in payload:
        result = payload["result"]
        msg_id = int(payload.get("id", 0))

        if msg_id in mcp_client.call_results:
            logger.bind(tag=TAG).debug(f"Received tool call response for ID: {msg_id}")
            await mcp_client.resolve_call_result(msg_id, result)
            return

        if msg_id == 1:  # mcpInitializeID
            logger.bind(tag=TAG).debug("Received MCP initialization response")
            server_info = result.get("serverInfo")
            if isinstance(server_info, dict):
                name = server_info.get("name")
                version = server_info.get("version")
                logger.bind(tag=TAG).info(f"Client MCP Server: {name} v{version}")
            return

        elif msg_id == 2:  # mcpToolsListID
            logger.bind(tag=TAG).debug("Received MCP tools list response")
            if isinstance(result, dict) and "tools" in result:
                tools_data = result["tools"]
                if not isinstance(tools_data, list):
                    logger.bind(tag=TAG).error("Tool list format is invalid")
                    return

                logger.bind(tag=TAG).info(f"Client device supports {len(tools_data)} tools")

                for i, tool in enumerate(tools_data):
                    if not isinstance(tool, dict):
                        continue

                    name = tool.get("name", "")
                    description = tool.get("description", "")
                    input_schema = {"type": "object", "properties": {}, "required": []}

                    if "inputSchema" in tool and isinstance(tool["inputSchema"], dict):
                        schema = tool["inputSchema"]
                        input_schema["type"] = schema.get("type", "object")
                        input_schema["properties"] = schema.get("properties", {})
                        input_schema["required"] = [
                            s for s in schema.get("required", []) if isinstance(s, str)
                        ]

                    new_tool = {
                        "name": name,
                        "description": description,
                        "inputSchema": input_schema,
                    }
                    await mcp_client.add_tool(new_tool)

                # Replace tool names in descriptions for consistency
                for tool_data in mcp_client.tools.values():
                    if "description" in tool_data:
                        description = tool_data["description"]
                        for sanitized_name, original_name in mcp_client.name_mapping.items():
                            description = description.replace(original_name, sanitized_name)
                        tool_data["description"] = description

                next_cursor = result.get("nextCursor", "")
                if next_cursor:
                    logger.bind(tag=TAG).debug(f"Paginating tools, nextCursor: {next_cursor}")
                    await send_mcp_tools_list_continue_request(conn, next_cursor)
                else:
                    await mcp_client.set_ready(True)
                    logger.bind(tag=TAG).info(f"All tools retrieved, MCP client ready. Available tools: {list(mcp_client.tools.keys())}")

                    # Launch tool refresh in background to prevent blocking
                    if hasattr(conn, "func_handler") and conn.func_handler:
                        asyncio.create_task(_background_tool_refresh(conn))
            return

    # Handle incoming method requests from client
    elif "method" in payload:
        method = payload["method"]
        logger.bind(tag=TAG).info(f"Received MCP client request: {method}")

    # Handle error payloads
    elif "error" in payload:
        error_data = payload["error"]
        error_msg = error_data.get("message", "Unknown error")
        logger.bind(tag=TAG).error(f"Received MCP error response: {error_msg}")

        msg_id = int(payload.get("id", 0))
        if msg_id in mcp_client.call_results:
            await mcp_client.reject_call_result(msg_id, Exception(f"MCP Error: {error_msg}"))


#async def send_mcp_initialize_message(conn):
#    """Send MCP initialization message"""
#    vision_url = get_vision_url(conn.config)
#    auth = AuthToken(conn.config["server"]["auth_key"])
#    token = auth.generate_token(conn.headers.get("device-id"))
#
#    vision = {"url": vision_url, "token": token}
#
#    payload = {
#        "jsonrpc": "2.0",
#        "id": 1,
#        "method": "initialize",
#        "params": {
#            "protocolVersion": "2024-11-05",
#            "capabilities": {
#                "roots": {"listChanged": True},
#                "sampling": {},
#                "vision": vision,
#            },
#            "clientInfo": {"name": "XiaozhiClient", "version": "1.0.0"},
#        },
#    }
#    logger.bind(tag=TAG).debug("Sending MCP initialize message...")
#    await send_mcp_message(conn, payload)

async def send_mcp_initialize_message(conn):
    """Simplified MCP initialization to prevent DNS/Auth hangs"""
    # We are skipping get_vision_url and AuthToken generation for now
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "roots": {"listChanged": True},
                "sampling": {},
                # Vision and Auth are omitted to test for network hangs
            },
            "clientInfo": {"name": "XiaozhiClient", "version": "1.0.0"},
        },
    }
    logger.bind(tag=TAG).debug("Sending simplified MCP initialize message...")
    await send_mcp_message(conn, payload)

async def send_mcp_tools_list_request(conn):
    """Send MCP tools list request"""
    payload = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
    logger.bind(tag=TAG).debug("Requesting MCP tool list...")
    await send_mcp_message(conn, payload)


async def send_mcp_tools_list_continue_request(conn, cursor: str):
    """Send continuation request for tools list"""
    payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {"cursor": cursor},
    }
    logger.bind(tag=TAG).info(f"Continuing tool list request with cursor: {cursor}")
    await send_mcp_message(conn, payload)


async def call_mcp_tool(conn, mcp_client: MCPClient, tool_name: str, args: str = "{}", timeout: int = 30):
    """Call a specified MCP tool and await response"""
    if not await mcp_client.is_ready():
        raise RuntimeError("MCP client is not ready yet")

    if not mcp_client.has_tool(tool_name):
        raise ValueError(f"Tool {tool_name} does not exist")

    tool_call_id = await mcp_client.get_next_id()
    result_future = asyncio.Future()
    await mcp_client.register_call_result_future(tool_call_id, result_future)

    try:
        if isinstance(args, str):
            if not args.strip():
                arguments = {}
            else:
                try:
                    arguments = json.loads(args)
                except json.JSONDecodeError:
                    json_objects = re.findall(r"\{[^{}]*\}", args)
                    if len(json_objects) > 1:
                        merged_dict = {}
                        for json_str in json_objects:
                            try:
                                obj = json.loads(json_str)
                                if isinstance(obj, dict):
                                    merged_dict.update(obj)
                            except json.JSONDecodeError:
                                continue
                        if merged_dict:
                            arguments = merged_dict
                        else:
                            raise ValueError(f"Could not parse valid JSON from: {args}")
                    else:
                        raise ValueError(f"JSON parsing failed for args: {args}")
        elif isinstance(args, dict):
            arguments = args
        else:
            raise ValueError(f"Invalid args type: {type(args)}")

        if not isinstance(arguments, dict):
            raise ValueError(f"Arguments must be a dictionary, got: {type(arguments)}")

    except Exception as e:
        if not isinstance(e, ValueError):
            raise ValueError(f"Argument processing failed: {str(e)}")
        raise e

    actual_name = mcp_client.name_mapping.get(tool_name, tool_name)
    payload = {
        "jsonrpc": "2.0",
        "id": tool_call_id,
        "method": "tools/call",
        "params": {"name": actual_name, "arguments": arguments},
    }

    logger.bind(tag=TAG).info(f"Initiating tool call: {actual_name} with args: {args}")
    await send_mcp_message(conn, payload)

    try:
        raw_result = await asyncio.wait_for(result_future, timeout=timeout)
        logger.bind(tag=TAG).info(f"Tool call {actual_name} successful")

        if isinstance(raw_result, dict):
            if raw_result.get("isError") is True:
                error_msg = raw_result.get("error", "No detailed error provided")
                raise RuntimeError(f"Tool execution error: {error_msg}")

            content = raw_result.get("content")
            if isinstance(content, list) and len(content) > 0:
                if isinstance(content[0], dict) and "text" in content[0]:
                    result_text = content[0]["text"]
                    
                    # Inject server time if this is the device status tool
                    if "get_device_status" in actual_name:
                        try:
                            status_data = json.loads(result_text)
                            if isinstance(status_data, dict):
                                status_data["server_timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                status_data["server_weekday"] = datetime.now().strftime("%A")
                                result_text = json.dumps(status_data, ensure_ascii=False)
                        except:
                            pass
                            
                    return result_text
        return str(raw_result)
    except asyncio.TimeoutError:
        await mcp_client.cleanup_call_result(tool_call_id)
        raise TimeoutError("The tool call request timed out")
    except Exception as e:
        await mcp_client.cleanup_call_result(tool_call_id)
        raise e

async def sync_device_hardware_status(conn, tool_name="get_device_status"):
    """Helper to fetch hardware status (battery, volume, charging, brightness) via MCP"""
    try:
        logger.bind(tag=TAG).info(f"Initiating MCP hardware sync via {tool_name}...")
        res = await call_mcp_tool(conn, conn.mcp_client, tool_name)
        data = json.loads(res)
        if isinstance(data, dict):
            # 1. Battery Sync
            battery_data = data.get("battery") or data
            bat = battery_data.get("level") if isinstance(battery_data, dict) else battery_data
            if bat is not None:
                conn.mcp_battery = str(bat)
                logger.bind(tag=TAG).info(f"MCP hardware sync - battery: {bat}%")
            
            charging = battery_data.get("charging") if isinstance(battery_data, dict) else None
            if charging is not None:
                conn.mcp_charging = "charging" if charging else "not charging"
                logger.bind(tag=TAG).info(f"MCP hardware sync - charging: {conn.mcp_charging}")

            # 2. Volume Sync
            audio_data = data.get("audio_speaker") or data.get("audio") or data
            vol = audio_data.get("volume") if isinstance(audio_data, dict) else audio_data
            if vol is not None:
                conn.mcp_volume = str(vol)
                logger.bind(tag=TAG).info(f"MCP hardware sync - volume: {vol}%")
                
            # 3. Brightness Sync
            screen_data = data.get("screen") or data
            bright = screen_data.get("brightness") if isinstance(screen_data, dict) else None
            if bright is not None:
                conn.mcp_brightness = str(bright)
                logger.bind(tag=TAG).info(f"MCP hardware sync - brightness: {bright}%")
                
            if bat is None and vol is None:
                logger.bind(tag=TAG).warning(f"MCP hardware sync - no primary data found in response: {data}")
    except Exception as e:
        logger.bind(tag=TAG).warning(f"MCP hardware status sync failed: {e}")

