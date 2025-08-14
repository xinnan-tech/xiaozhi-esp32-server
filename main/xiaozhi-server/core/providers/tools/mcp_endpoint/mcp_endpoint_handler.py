"""MCP endpoint handler"""

import json
import asyncio
import re
import websockets
from config.logger import setup_logging
from .mcp_endpoint_client import MCPEndpointClient

TAG = __name__
logger = setup_logging()


async def connect_mcp_endpoint(mcp_endpoint_url: str, conn=None) -> MCPEndpointClient:
    """Connect to MCP endpoint"""
    if not mcp_endpoint_url or "你的" in mcp_endpoint_url or mcp_endpoint_url == "null":
        return None

    try:
        websocket = await websockets.connect(mcp_endpoint_url)
        mcp_client = MCPEndpointClient(conn)
        mcp_client.set_websocket(websocket)

        # Start message listener
        asyncio.create_task(_message_listener(mcp_client))

        # Send initialization message
        await send_mcp_endpoint_initialize(mcp_client)

        # Send initialization complete notification
        await send_mcp_endpoint_notification(mcp_client, "notifications/initialized")

        # Get tools list
        await send_mcp_endpoint_tools_list(mcp_client)

        logger.bind(tag=TAG).info("MCP endpoint connection successful")
        return mcp_client

    except Exception as e:
        logger.bind(tag=TAG).error(f"Failed to connect to MCP endpoint: {e}")
        return None


async def _message_listener(mcp_client: MCPEndpointClient):
    """Listen for MCP endpoint messages"""
    try:
        async for message in mcp_client.websocket:
            await handle_mcp_endpoint_message(mcp_client, message)
    except websockets.exceptions.ConnectionClosed:
        logger.bind(tag=TAG).info("MCP endpoint connection closed")
    except Exception as e:
        logger.bind(tag=TAG).error(f"MCP endpoint message listener error: {e}")
    finally:
        await mcp_client.set_ready(False)


async def handle_mcp_endpoint_message(mcp_client: MCPEndpointClient, message: str):
    """Handle MCP endpoint messages"""
    try:
        payload = json.loads(message)
        logger.bind(tag=TAG).debug(f"Received MCP endpoint message: {payload}")

        if not isinstance(payload, dict):
            logger.bind(tag=TAG).error("MCP endpoint message format error")
            return

        # Handle result
        if "result" in payload:
            result = payload["result"]
            # Safely get message ID, use 0 if None
            msg_id_raw = payload.get("id")
            msg_id = int(msg_id_raw) if msg_id_raw is not None else 0

            # Check for tool call response first
            if msg_id in mcp_client.call_results:
                logger.bind(tag=TAG).debug(
                    f"Received tool call response, ID: {msg_id}, Result: {result}"
                )
                await mcp_client.resolve_call_result(msg_id, result)
                return

            if msg_id == 1:  # mcpInitializeID
                logger.bind(tag=TAG).debug(
                    "Received MCP endpoint initialization response")
                if result is not None and isinstance(result, dict):
                    server_info = result.get("serverInfo")
                    if isinstance(server_info, dict):
                        name = server_info.get("name")
                        version = server_info.get("version")
                        logger.bind(tag=TAG).info(
                            f"MCP endpoint server info: name={name}, version={version}"
                        )
                else:
                    logger.bind(tag=TAG).warning(
                        "MCP endpoint initialization response result is empty or format error"
                    )
                return

            elif msg_id == 2:  # mcpToolsListID
                logger.bind(tag=TAG).debug(
                    "Received MCP endpoint tools list response")
                if (
                    result is not None
                    and isinstance(result, dict)
                    and "tools" in result
                ):
                    tools_data = result["tools"]
                    if not isinstance(tools_data, list):
                        logger.bind(tag=TAG).error("Tools list format error")
                        return

                    logger.bind(tag=TAG).info(
                        f"MCP endpoint supported tools count: {len(tools_data)}"
                    )

                    for i, tool in enumerate(tools_data):
                        if not isinstance(tool, dict):
                            continue

                        name = tool.get("name", "")
                        description = tool.get("description", "")
                        input_schema = {
                            "type": "object",
                            "properties": {},
                            "required": [],
                        }

                        if "inputSchema" in tool and isinstance(
                            tool["inputSchema"], dict
                        ):
                            schema = tool["inputSchema"]
                            input_schema["type"] = schema.get("type", "object")
                            input_schema["properties"] = schema.get(
                                "properties", {})
                            input_schema["required"] = [
                                s
                                for s in schema.get("required", [])
                                if isinstance(s, str)
                            ]

                        new_tool = {
                            "name": name,
                            "description": description,
                            "inputSchema": input_schema,
                        }

                        await mcp_client.add_tool(new_tool)
                        logger.bind(tag=TAG).debug(
                            f"MCP endpoint tool #{i+1}: {name}")

                    # Replace all tool names in tool descriptions
                    for tool_data in mcp_client.tools.values():
                        if "description" in tool_data:
                            description = tool_data["description"]
                            # Iterate through all tool names for replacement
                            for (
                                sanitized_name,
                                original_name,
                            ) in mcp_client.name_mapping.items():
                                description = description.replace(
                                    original_name, sanitized_name
                                )
                            tool_data["description"] = description

                    next_cursor = (
                        result.get(
                            "nextCursor", "") if result is not None else ""
                    )

                    if next_cursor:
                        logger.bind(tag=TAG).info(
                            f"More tools available, nextCursor: {next_cursor}"
                        )
                        await send_mcp_endpoint_tools_list_continue(
                            mcp_client, next_cursor
                        )
                    else:
                        await mcp_client.set_ready(True)
                        logger.bind(tag=TAG).info(
                            "All MCP endpoint tools retrieved, client ready"
                        )

                        # Refresh tool cache to ensure MCP endpoint tools are included in function list
                        if (
                            hasattr(mcp_client, "conn")
                            and mcp_client.conn
                            and hasattr(mcp_client.conn, "func_handler")
                            and mcp_client.conn.func_handler
                        ):
                            mcp_client.conn.func_handler.tool_manager.refresh_tools()
                            mcp_client.conn.func_handler.current_support_functions()

                        logger.bind(tag=TAG).info(
                            f"MCP endpoint tools retrieval completed, total {len(mcp_client.tools)} tools"
                        )
                else:
                    logger.bind(tag=TAG).warning(
                        "MCP endpoint tools list response result is empty or format error"
                    )
                return

        # Handle method calls (requests from the endpoint)
        elif "method" in payload:
            method = payload["method"]
            logger.bind(tag=TAG).info(
                f"Received MCP endpoint request: {method}")

        elif "error" in payload:
            error_data = payload["error"]
            error_msg = error_data.get("message", "Unknown error")
            logger.bind(tag=TAG).error(
                f"Received MCP endpoint error response: {error_msg}")

            # Safely get message ID, use 0 if None
            msg_id_raw = payload.get("id")
            msg_id = int(msg_id_raw) if msg_id_raw is not None else 0

            if msg_id in mcp_client.call_results:
                await mcp_client.reject_call_result(
                    msg_id, Exception(f"MCP endpoint error: {error_msg}")
                )

    except json.JSONDecodeError as e:
        logger.bind(tag=TAG).error(
            f"MCP endpoint message JSON parsing failed: {e}")
    except Exception as e:
        logger.bind(tag=TAG).error(f"Error handling MCP endpoint message: {e}")
        import traceback
        logger.bind(tag=TAG).error(f"Error details: {traceback.format_exc()}")


async def send_mcp_endpoint_initialize(mcp_client: MCPEndpointClient):
    """Send MCP endpoint initialization message"""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,  # mcpInitializeID
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "roots": {"listChanged": True},
                "sampling": {},
            },
            "clientInfo": {
                "name": "XiaozhiMCPEndpointClient",
                "version": "1.0.0",
            },
        },
    }

    message = json.dumps(payload)
    logger.bind(tag=TAG).info("Sending MCP endpoint initialization message")
    await mcp_client.send_message(message)


async def send_mcp_endpoint_notification(mcp_client: MCPEndpointClient, method: str):
    """Send MCP endpoint notification message"""
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": {},
    }

    message = json.dumps(payload)
    logger.bind(tag=TAG).debug(f"Sending MCP endpoint notification: {method}")
    await mcp_client.send_message(message)


async def send_mcp_endpoint_tools_list(mcp_client: MCPEndpointClient):
    """Send MCP endpoint tools list request"""
    payload = {
        "jsonrpc": "2.0",
        "id": 2,  # mcpToolsListID
        "method": "tools/list",
    }

    message = json.dumps(payload)
    logger.bind(tag=TAG).debug("Sending MCP endpoint tools list request")
    await mcp_client.send_message(message)


async def send_mcp_endpoint_tools_list_continue(
    mcp_client: MCPEndpointClient, cursor: str
):
    """Send MCP endpoint tools list request with cursor"""
    payload = {
        "jsonrpc": "2.0",
        "id": 2,  # mcpToolsListID (same ID for continuation)
        "method": "tools/list",
        "params": {"cursor": cursor},
    }

    message = json.dumps(payload)
    logger.bind(tag=TAG).info(
        f"Sending MCP endpoint tools list request with cursor: {cursor}")
    await mcp_client.send_message(message)


async def call_mcp_endpoint_tool(
    mcp_client: MCPEndpointClient, tool_name: str, args: str = "{}", timeout: int = 30
):
    """
    Call the specified MCP endpoint tool and wait for response
    """
    if not await mcp_client.is_ready():
        raise RuntimeError("MCP endpoint client not ready yet")

    if not mcp_client.has_tool(tool_name):
        raise ValueError(f"Tool {tool_name} does not exist")

    tool_call_id = await mcp_client.get_next_id()
    result_future = asyncio.Future()
    await mcp_client.register_call_result_future(tool_call_id, result_future)

    # Handle parameters
    try:
        if isinstance(args, str):
            # Ensure string is valid JSON
            if not args.strip():
                arguments = {}
            else:
                try:
                    # Try to parse directly
                    arguments = json.loads(args)
                except json.JSONDecodeError:
                    # If parsing fails, try to merge multiple JSON objects
                    try:
                        # Use regex to match all JSON objects
                        json_objects = re.findall(r"\{[^{}]*\}", args)
                        if len(json_objects) > 1:
                            # Merge all JSON objects
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
                                raise ValueError(
                                    f"Cannot parse any valid JSON objects: {args}")
                        else:
                            raise ValueError(
                                f"Parameter JSON parsing failed: {args}")
                    except Exception as e:
                        logger.bind(tag=TAG).error(
                            f"Parameter JSON parsing failed: {str(e)}, Original parameters: {args}"
                        )
                        raise ValueError(
                            f"Parameter JSON parsing failed: {str(e)}")
        elif isinstance(args, dict):
            arguments = args
        else:
            raise ValueError(
                f"Parameter type error, expected string or dictionary, actual type: {type(args)}")

        # Ensure parameters are dictionary type
        if not isinstance(arguments, dict):
            raise ValueError(
                f"Parameters must be dictionary type, actual type: {type(arguments)}")

    except Exception as e:
        if not isinstance(e, ValueError):
            raise ValueError(f"Parameter processing failed: {str(e)}")
        raise e

    actual_name = mcp_client.name_mapping.get(tool_name, tool_name)

    payload = {
        "jsonrpc": "2.0",
        "id": tool_call_id,
        "method": "tools/call",
        "params": {"name": actual_name, "arguments": arguments},
    }

    message = json.dumps(payload)
    logger.bind(tag=TAG).info(
        f"Sending MCP endpoint tool call request: {actual_name}, Parameters: {args}")
    await mcp_client.send_message(message)

    try:
        # Wait for response or timeout
        raw_result = await asyncio.wait_for(result_future, timeout=timeout)
        logger.bind(tag=TAG).info(
            f"MCP endpoint tool call {actual_name} successful, Raw result: {raw_result}"
        )

        if isinstance(raw_result, dict):
            if raw_result.get("isError") is True:
                error_msg = raw_result.get(
                    "error", "Tool call returned error but did not provide specific error information"
                )
                raise RuntimeError(f"Tool call error: {error_msg}")

            content = raw_result.get("content")
            if isinstance(content, list) and len(content) > 0:
                if isinstance(content[0], dict) and "text" in content[0]:
                    # Return text content directly without JSON parsing
                    return content[0]["text"]

        # If result is not in expected format, convert to string
        return str(raw_result)

    except asyncio.TimeoutError:
        await mcp_client.cleanup_call_result(tool_call_id)
        raise TimeoutError("Tool call request timeout")
    except Exception as e:
        await mcp_client.cleanup_call_result(tool_call_id)
        raise e
