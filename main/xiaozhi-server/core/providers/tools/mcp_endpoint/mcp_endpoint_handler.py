"""MCP接入点处理器"""

import json
import asyncio
import re
import websockets
from config.logger import setup_logging
from .mcp_endpoint_client import MCPEndpointClient

TAG = __name__
logger = setup_logging()


async def connect_mcp_endpoint(mcp_endpoint_url: str, conn=None) -> MCPEndpointClient:
    """连接到MCP接入点"""
    if not mcp_endpoint_url or "你的" in mcp_endpoint_url or mcp_endpoint_url == "null":
        return None

    try:
        websocket = await websockets.connect(mcp_endpoint_url)

        mcp_client = MCPEndpointClient(conn)
        mcp_client.set_websocket(websocket)

        # 启动消息监听器
        asyncio.create_task(_message_listener(mcp_client))

        # 发送初始化消息
        await send_mcp_endpoint_initialize(mcp_client)

        # 发送初始化完成通知
        await send_mcp_endpoint_notification(mcp_client, "notifications/initialized")

        # 获取工具列表
        await send_mcp_endpoint_tools_list(mcp_client)

        logger.bind(tag=TAG).info("MCP接入点连接成功")
        return mcp_client

    except Exception as e:
        logger.bind(tag=TAG).error(f"连接MCP接入点失败: {e}")
        return None


async def _message_listener(mcp_client: MCPEndpointClient):
    """监听MCP接入点消息"""
    try:
        async for message in mcp_client.websocket:
            await handle_mcp_endpoint_message(mcp_client, message)
    except websockets.exceptions.ConnectionClosed:
        logger.bind(tag=TAG).info("MCP接入点连接已关闭")
    except Exception as e:
        logger.bind(tag=TAG).error(f"MCP接入点消息监听器错误: {e}")
    finally:
        await mcp_client.set_ready(False)


async def handle_mcp_endpoint_message(mcp_client: MCPEndpointClient, message: str):
    """处理MCP接入点消息"""
    try:
        payload = json.loads(message)
        logger.bind(tag=TAG).debug(f"收到MCP接入点消息: {payload}")

        if not isinstance(payload, dict):
            logger.bind(tag=TAG).error("MCP接入点消息格式错误")
            return

        # Handle result
        if "result" in payload:
            result = payload["result"]
            # 安全地获取消息ID，如果为None则使用0
            msg_id_raw = payload.get("id")
            msg_id = int(msg_id_raw) if msg_id_raw is not None else 0

            # Check for tool call response first
            if msg_id in mcp_client.call_results:
                logger.bind(tag=TAG).debug(
                    f"收到工具调用响应，ID: {msg_id}, 结果: {result}"
                )
                await mcp_client.resolve_call_result(msg_id, result)
                return

            if msg_id == 1:  # mcpInitializeID
                logger.bind(tag=TAG).debug("收到MCP接入点初始化响应")
                if result is not None and isinstance(result, dict):
                    server_info = result.get("serverInfo")
                    if isinstance(server_info, dict):
                        name = server_info.get("name")
                        version = server_info.get("version")
                        logger.bind(tag=TAG).info(
                            f"MCP接入点服务器信息: name={name}, version={version}"
                        )
                else:
                    logger.bind(tag=TAG).warning(
                        "MCP接入点初始化响应结果为空或格式错误"
                    )
                return

            elif msg_id == 2:  # mcpToolsListID
                logger.bind(tag=TAG).debug("收到MCP接入点工具列表响应")
                if (
                    result is not None
                    and isinstance(result, dict)
                    and "tools" in result
                ):
                    tools_data = result["tools"]
                    if not isinstance(tools_data, list):
                        logger.bind(tag=TAG).error("工具列表格式错误")
                        return

                    logger.bind(tag=TAG).info(
                        f"MCP接入点支持的工具数量: {len(tools_data)}"
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
                            input_schema["properties"] = schema.get("properties", {})
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
                        logger.bind(tag=TAG).debug(f"MCP接入点工具 #{i+1}: {name}")

                    # 替换所有工具描述中的工具名称
                    for tool_data in mcp_client.tools.values():
                        if "description" in tool_data:
                            description = tool_data["description"]
                            # 遍历所有工具名称进行替换
                            for (
                                sanitized_name,
                                original_name,
                            ) in mcp_client.name_mapping.items():
                                description = description.replace(
                                    original_name, sanitized_name
                                )
                            tool_data["description"] = description

                    next_cursor = (
                        result.get("nextCursor", "") if result is not None else ""
                    )
                    if next_cursor:
                        logger.bind(tag=TAG).info(
                            f"有更多工具，nextCursor: {next_cursor}"
                        )
                        await send_mcp_endpoint_tools_list_continue(
                            mcp_client, next_cursor
                        )
                    else:
                        await mcp_client.set_ready(True)
                        logger.bind(tag=TAG).info(
                            "所有MCP接入点工具已获取，客户端准备就绪"
                        )

                        # 刷新工具缓存，确保MCP接入点工具被包含在函数列表中
                        if (
                            hasattr(mcp_client, "conn")
                            and mcp_client.conn
                            and hasattr(mcp_client.conn, "func_handler")
                            and mcp_client.conn.func_handler
                        ):
                            mcp_client.conn.func_handler.tool_manager.refresh_tools()
                            mcp_client.conn.func_handler.current_support_functions()

                        logger.bind(tag=TAG).info(
                            f"MCP接入点工具获取完成，共 {len(mcp_client.tools)} 个工具"
                        )
                else:
                    logger.bind(tag=TAG).warning(
                        "MCP接入点工具列表响应结果为空或格式错误"
                    )
                return

        # Handle method calls (requests from the endpoint)
        elif "method" in payload:
            method = payload["method"]
            logger.bind(tag=TAG).info(f"收到MCP接入点请求: {method}")

        elif "error" in payload:
            error_data = payload["error"]
            error_msg = error_data.get("message", "未知错误")
            logger.bind(tag=TAG).error(f"收到MCP接入点错误响应: {error_msg}")

            # 安全地获取消息ID，如果为None则使用0
            msg_id_raw = payload.get("id")
            msg_id = int(msg_id_raw) if msg_id_raw is not None else 0

            if msg_id in mcp_client.call_results:
                await mcp_client.reject_call_result(
                    msg_id, Exception(f"MCP接入点错误: {error_msg}")
                )

    except json.JSONDecodeError as e:
        logger.bind(tag=TAG).error(f"MCP接入点消息JSON解析失败: {e}")
    except Exception as e:
        logger.bind(tag=TAG).error(f"处理MCP接入点消息时出错: {e}")
        import traceback

        logger.bind(tag=TAG).error(f"错误详情: {traceback.format_exc()}")


async def send_mcp_endpoint_initialize(mcp_client: MCPEndpointClient):
    """发送MCP接入点初始化消息"""
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
    logger.bind(tag=TAG).info("发送MCP接入点初始化消息")
    await mcp_client.send_message(message)


async def send_mcp_endpoint_notification(mcp_client: MCPEndpointClient, method: str):
    """发送MCP接入点通知消息"""
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": {},
    }
    message = json.dumps(payload)
    logger.bind(tag=TAG).debug(f"发送MCP接入点通知: {method}")
    await mcp_client.send_message(message)


async def send_mcp_endpoint_tools_list(mcp_client: MCPEndpointClient):
    """发送MCP接入点工具列表请求"""
    payload = {
        "jsonrpc": "2.0",
        "id": 2,  # mcpToolsListID
        "method": "tools/list",
    }
    message = json.dumps(payload)
    logger.bind(tag=TAG).debug("发送MCP接入点工具列表请求")
    await mcp_client.send_message(message)


async def send_mcp_endpoint_tools_list_continue(
    mcp_client: MCPEndpointClient, cursor: str
):
    """发送带有cursor的MCP接入点工具列表请求"""
    payload = {
        "jsonrpc": "2.0",
        "id": 2,  # mcpToolsListID (same ID for continuation)
        "method": "tools/list",
        "params": {"cursor": cursor},
    }
    message = json.dumps(payload)
    logger.bind(tag=TAG).info(f"发送带cursor的MCP接入点工具列表请求: {cursor}")
    await mcp_client.send_message(message)


async def call_mcp_endpoint_tool(
    mcp_client: MCPEndpointClient, tool_name: str, args: str = "{}", timeout: int = 30
):
    """
    调用指定的MCP接入点工具，并等待响应
    """
    if not await mcp_client.is_ready():
        raise RuntimeError("MCP接入点客户端尚未准备就绪")

    if not mcp_client.has_tool(tool_name):
        raise ValueError(f"工具 {tool_name} 不存在")

    tool_call_id = await mcp_client.get_next_id()
    result_future = asyncio.Future()
    await mcp_client.register_call_result_future(tool_call_id, result_future)

    # 处理参数
    try:
        if isinstance(args, str):
            # 确保字符串是有效的JSON
            if not args.strip():
                arguments = {}
            else:
                try:
                    # 尝试直接解析
                    arguments = json.loads(args)
                except json.JSONDecodeError:
                    # 如果解析失败，尝试合并多个JSON对象
                    try:
                        # 使用正则表达式匹配所有JSON对象
                        json_objects = re.findall(r"\{[^{}]*\}", args)
                        if len(json_objects) > 1:
                            # 合并所有JSON对象
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
                                raise ValueError(f"无法解析任何有效的JSON对象: {args}")
                        else:
                            raise ValueError(f"参数JSON解析失败: {args}")
                    except Exception as e:
                        logger.bind(tag=TAG).error(
                            f"参数JSON解析失败: {str(e)}, 原始参数: {args}"
                        )
                        raise ValueError(f"参数JSON解析失败: {str(e)}")
        elif isinstance(args, dict):
            arguments = args
        else:
            raise ValueError(f"参数类型错误，期望字符串或字典，实际类型: {type(args)}")

        # 确保参数是字典类型
        if not isinstance(arguments, dict):
            raise ValueError(f"参数必须是字典类型，实际类型: {type(arguments)}")

    except Exception as e:
        if not isinstance(e, ValueError):
            raise ValueError(f"参数处理失败: {str(e)}")
        raise e

    actual_name = mcp_client.name_mapping.get(tool_name, tool_name)
    payload = {
        "jsonrpc": "2.0",
        "id": tool_call_id,
        "method": "tools/call",
        "params": {"name": actual_name, "arguments": arguments},
    }

    message = json.dumps(payload)
    logger.bind(tag=TAG).info(f"发送MCP接入点工具调用请求: {actual_name}，参数: {args}")
    await mcp_client.send_message(message)

    try:
        # Wait for response or timeout
        raw_result = await asyncio.wait_for(result_future, timeout=timeout)
        logger.bind(tag=TAG).info(
            f"MCP接入点工具调用 {actual_name} 成功，原始结果: {raw_result}"
        )

        if isinstance(raw_result, dict):
            if raw_result.get("isError") is True:
                error_msg = raw_result.get(
                    "error", "工具调用返回错误，但未提供具体错误信息"
                )
                raise RuntimeError(f"工具调用错误: {error_msg}")

            content = raw_result.get("content")
            if isinstance(content, list) and len(content) > 0:
                if isinstance(content[0], dict) and "text" in content[0]:
                    # 直接返回文本内容，不进行JSON解析
                    return content[0]["text"]
        # 如果结果不是预期的格式，将其转换为字符串
        return str(raw_result)
    except asyncio.TimeoutError:
        await mcp_client.cleanup_call_result(tool_call_id)
        raise TimeoutError("工具调用请求超时")
    except Exception as e:
        await mcp_client.cleanup_call_result(tool_call_id)
        raise e
