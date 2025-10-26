"""服务端MCP管理器"""

import asyncio
import os
import json
from typing import Dict, Any, List
from config.config_loader import get_project_dir
from config.logger import setup_logging
from core.utils.auth import AuthToken
from .mcp_client import ServerMCPClient

TAG = __name__
logger = setup_logging()


class ServerMCPManager:
    """管理多个服务端MCP服务的集中管理器"""

    def __init__(self, conn) -> None:
        """初始化MCP管理器"""
        self.conn = conn
        self.config_path = get_project_dir() + "data/.mcp_server_settings.json"
        if not os.path.exists(self.config_path):
            self.config_path = ""
            logger.bind(tag=TAG).warning(
                f"请检查mcp服务配置文件：data/.mcp_server_settings.json"
            )
        self.clients: Dict[str, ServerMCPClient] = {}
        self.tools = []

        # 初始化加密的设备ID
        self.encrypted_device_id = self._get_encrypted_device_id()

    def load_config(self) -> Dict[str, Any]:
        """加载MCP服务配置"""
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

    def _get_encrypted_device_id(self) -> str:
        """获取加密后的设备ID"""
        try:
            # 获取加密密钥
            device_id_encrypt_key = self.conn.config.get("device_id_encrypt_key")

            # 验证密钥
            if not device_id_encrypt_key or "你" in device_id_encrypt_key:
                error_msg = "you need to set up device_id_encrypt_key"
                logger.bind(tag=TAG).error(error_msg)
            # 获取设备ID
            device_id = self.conn.headers.get("device-id") or getattr(self.conn, 'device_id', None)
            if not device_id:
                logger.bind(tag=TAG).error("无法获取设备ID")
                return "device_id not found"

            # 生成加密Token
            auth = AuthToken(device_id_encrypt_key)
            encrypt_device_id = auth.generate_token(device_id)
            logger.bind(tag=TAG).debug(f"设备ID已加密: {device_id}, Token长度: {len(encrypt_device_id)}")
            return encrypt_device_id

        except Exception as e:
            logger.bind(tag=TAG).error(f"设备ID加密失败: {e}")
            return f"encryption_error: {str(e)}"

    async def initialize_servers(self) -> None:
        """初始化所有MCP服务"""
        config = self.load_config()
        for name, srv_config in config.items():
            if not srv_config.get("command") and not srv_config.get("url"):
                logger.bind(tag=TAG).warning(
                    f"Skipping server {name}: neither command nor url specified"
                )
                continue

            try:
                # 初始化服务端MCP客户端
                logger.bind(tag=TAG).info(f"初始化服务端MCP客户端: {name}")
                client = ServerMCPClient(srv_config, self.conn)
                await client.initialize()
                self.clients[name] = client
                client_tools = client.get_available_tools()
                self.tools.extend(client_tools)

            except Exception as e:
                logger.bind(tag=TAG).error(
                    f"Failed to initialize MCP server {name}: {e}"
                )

        # 输出当前支持的服务端MCP工具列表
        if hasattr(self.conn, "func_handler") and self.conn.func_handler:
            # 刷新工具缓存以确保服务端MCP工具被正确加载
            if hasattr(self.conn.func_handler, "tool_manager"):
                self.conn.func_handler.tool_manager.refresh_tools()
            self.conn.func_handler.current_support_functions()

    def get_all_tools(self) -> List[Dict[str, Any]]:
        """获取所有服务的工具function定义"""
        return self.tools

    def is_mcp_tool(self, tool_name: str) -> bool:
        """检查是否是MCP工具"""
        for tool in self.tools:
            if (
                tool.get("function") is not None
                and tool["function"].get("name") == tool_name
            ):
                return True
        return False

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """执行工具调用，失败时会尝试重新连接"""
        logger.bind(tag=TAG).info(f"执行服务端MCP工具 {tool_name}，参数: {arguments}")

        max_retries = 3  # 最大重试次数
        retry_interval = 2  # 重试间隔(秒)

        # 找到对应的客户端
        client_name = None
        target_client = None
        for name, client in self.clients.items():
            if client.has_tool(tool_name):
                client_name = name
                target_client = client
                break

        if not target_client:
            raise ValueError(f"工具 {tool_name} 在任意MCP服务中未找到")
        
        # 注入加密的设备ID到参数中
        if self.encrypted_device_id:
            tool_data = target_client.tools_dict.get(tool_name)
            print("target_client", target_client)
            if tool_data and hasattr(tool_data, 'inputSchema') and isinstance(tool_data.inputSchema, dict):
                properties = tool_data.inputSchema.get('properties', {})
                if 'encrypted_device_id' in properties:    
                    arguments['encrypted_device_id'] = self.encrypted_device_id
                    logger.bind(tag=TAG).info(f"已注入加密设备ID到MCP工具参数中")

        # 带重试机制的工具调用
        for attempt in range(max_retries):
            try:
                return await target_client.call_tool(tool_name, arguments)
            except Exception as e:
                # 最后一次尝试失败时直接抛出异常
                if attempt == max_retries - 1:
                    raise

                logger.bind(tag=TAG).warning(
                    f"执行工具 {tool_name} 失败 (尝试 {attempt+1}/{max_retries}): {e}"
                )

                # 尝试重新连接
                logger.bind(tag=TAG).info(
                    f"重试前尝试重新连接 MCP 客户端 {client_name}"
                )
                try:
                    # 关闭旧的连接
                    await target_client.cleanup()

                    # 重新初始化客户端
                    config = self.load_config()
                    if client_name in config:
                        client = ServerMCPClient(config[client_name], self.conn)
                        await client.initialize()
                        self.clients[client_name] = client
                        target_client = client
                        logger.bind(tag=TAG).info(
                            f"成功重新连接 MCP 客户端: {client_name}"
                        )
                    else:
                        logger.bind(tag=TAG).error(
                            f"Cannot reconnect MCP client {client_name}: config not found"
                        )
                except Exception as reconnect_error:
                    logger.bind(tag=TAG).error(
                        f"Failed to reconnect MCP client {client_name}: {reconnect_error}"
                    )

                # 等待一段时间再重试
                await asyncio.sleep(retry_interval)

    async def cleanup_all(self) -> None:
        """关闭所有 MCP客户端"""
        for name, client in list(self.clients.items()):
            try:
                if hasattr(client, "cleanup"):
                    await asyncio.wait_for(client.cleanup(), timeout=20)
                logger.bind(tag=TAG).info(f"服务端MCP客户端已关闭: {name}")
            except (asyncio.TimeoutError, Exception) as e:
                logger.bind(tag=TAG).error(f"关闭服务端MCP客户端 {name} 时出错: {e}")
        self.clients.clear()
