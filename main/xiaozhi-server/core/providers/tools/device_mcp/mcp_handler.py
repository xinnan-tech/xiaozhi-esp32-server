"""Device-side MCP client support module"""

import json
import asyncio
import re
from concurrent.futures import Future
from core.utils.util import get_vision_url, sanitize_tool_name
from core.utils.auth import AuthToken
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


async def send_mcp_message(conn, payload: dict):
    """Helper to send MCP messages, encapsulating common logic."""
    if not conn.features.get("mcp"):
        logger.bind(tag=TAG).warning(
            "Client does not support MCP, cannot send MCP message")
        return

    message = json.dumps({"type": "mcp", "payload": payload})
    try:
        await conn.websocket.send(message)
        logger.bind(tag=TAG).info(f"Successfully sent MCP message: {message}")
    except Exception as e:
        logger.bind(tag=TAG).error(f"Failed to send MCP message: {e}")


async def handle_mcp_message(conn, mcp_client, payload: dict):
    """Handle MCP messages, including initialization, tool list and tool call responses"""
    logger.bind(tag=TAG).info(f"Handling MCP message: {str(payload)[:100]}")

    if not isinstance(payload, dict):
        logger.bind(tag=TAG).error(
            "MCP message missing payload field or format error")
        return

    # Handle result
    if "result" in payload:
        result = payload["result"]
        msg_id = int(payload.get("id", 0))

        # Check for tool call response first
        if msg_id in mcp_client.call_results:
            logger.bind(tag=TAG).debug(
                f"Received tool call response, ID: {msg_id}, Result: {result}"
            )
            await mcp_client.resolve_call_result(msg_id, result)
            return

        if msg_id == 1:  # mcpInitializeID
            logger.bind(tag=TAG).debug("Received MCP initialization response")
            server_info = result.get("serverInfo")
            if isinstance(server_info, dict):
                name = server_info.get("name")
                version = server_info.get("version")
                logger.bind(tag=TAG).info(
                    f"Client MCP server info: name={name}, version={version}"
                )
            return

        elif msg_id == 2:  # mcpToolsListID
            logger.bind(tag=TAG).debug("Received MCP tools list response")
            if isinstance(result, dict) and "tools" in result:
                tools_data = result["tools"]
                if not isinstance(tools_data, list):
                    logger.bind(tag=TAG).error("Tools list format error")
                    return

                logger.bind(tag=TAG).info(
                    f"Client device supported tools count: {len(tools_data)}"
                )

                for i, tool in enumerate(tools_data):
                    if not isinstance(tool, dict):
                        continue

                    name = tool.get("name", "")
                    description = tool.get("description", "")
                    input_schema = {"type": "object",
                                    "properties": {}, "required": []}

                    if "inputSchema" in tool and isinstance(tool["inputSchema"], dict):
                        schema = tool["inputSchema"]
                        input_schema["type"] = schema.get("type", "object")
                        input_schema["properties"] = schema.get(
                            "properties", {})
                        input_schema["required"] = [
                            s for s in schema.get("required", []) if isinstance(s, str)
                        ]

                    new_tool = {
                        "name": name,
                        "description": description,
                        "inputSchema": input_schema,
                    }

                    await mcp_client.add_tool(new_tool)
                    logger.bind(tag=TAG).debug(f"Client tool #{i+1}: {name}")

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

                next_cursor = result.get("nextCursor", "")
                if next_cursor:
                    logger.bind(tag=TAG).info(
                        f"More tools available, nextCursor: {next_cursor}")
                    await send_mcp_tools_list_continue_request(conn, next_cursor)
                else:
                    await mcp_client.set_ready(True)
                    logger.bind(tag=TAG).info(
                        "All tools retrieved, MCP client ready")

                    # Refresh tool cache to ensure MCP tools are included in function list
                    if hasattr(conn, "func_handler") and conn.func_handler:
                        conn.func_handler.tool_manager.refresh_tools()
                        conn.func_handler.current_support_functions()
            return

    # Handle method calls (requests from the client)
    elif "method" in payload:
        method = payload["method"]
        logger.bind(tag=TAG).info(f"Received MCP client request: {method}")

    elif "error" in payload:
        error_data = payload["error"]
        error_msg = error_data.get("message", "Unknown error")
        logger.bind(tag=TAG).error(f"Received MCP error response: {error_msg}")

        msg_id = int(payload.get("id", 0))
        if msg_id in mcp_client.call_results:
            await mcp_client.reject_call_result(
                msg_id, Exception(f"MCP error: {error_msg}")
            )


async def send_mcp_initialize_message(conn):
    """Send MCP initialization message"""
    vision_url = get_vision_url(conn.config)
    # Generate token using key
    auth = AuthToken(conn.config["server"]["auth_key"])
    token = auth.generate_token(conn.headers.get("device-id"))

    vision = {
        "url": vision_url,
        "token": token,
    }

    payload = {
        "jsonrpc": "2.0",
        "id": 1,  # mcpInitializeID
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "roots": {"listChanged": True},
                "sampling": {},
                "vision": vision,
            },
            "clientInfo": {
                "name": "XiaozhiClient",
                "version": "1.0.0",
            },
        },
    }

    logger.bind(tag=TAG).info("Sending MCP initialization message")
    await send_mcp_message(conn, payload)


async def send_mcp_tools_list_request(conn):
    """Send MCP tools list request"""
    payload = {
        "jsonrpc": "2.0",
        "id": 2,  # mcpToolsListID
        "method": "tools/list",
    }

    logger.bind(tag=TAG).debug("Sending MCP tools list request")
    await send_mcp_message(conn, payload)


async def send_mcp_tools_list_continue_request(conn, cursor: str):
    """Send MCP tools list request with cursor"""
    payload = {
        "jsonrpc": "2.0",
        "id": 2,  # mcpToolsListID (same ID for continuation)
        "method": "tools/list",
        "params": {"cursor": cursor},
    }

    logger.bind(tag=TAG).info(
        f"Sending MCP tools list request with cursor: {cursor}")
    await send_mcp_message(conn, payload)


async def call_mcp_tool(
    conn, mcp_client, tool_name: str, args: str = "{}", timeout: int = 30
):
    """Call the specified tool and wait for response"""
    if not await mcp_client.is_ready():
        raise RuntimeError("MCP client is not ready yet")

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

    logger.bind(tag=TAG).info(
        f"Sending client MCP tool call request: {actual_name}, Parameters: {args}")
    await send_mcp_message(conn, payload)

    try:
        # Wait for response or timeout
        raw_result = await asyncio.wait_for(result_future, timeout=timeout)
        logger.bind(tag=TAG).info(
            f"Client MCP tool call {actual_name} successful, Raw result: {raw_result}"
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
