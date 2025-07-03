"""工具系统的类型定义"""

from enum import Enum

from dataclasses import dataclass
from typing import Any, Dict, Optional
from plugins_func.register import Action


class ToolType(Enum):
    """工具类型枚举"""

    SERVER_PLUGIN = "server_plugin"  # 服务端插件
    SERVER_MCP = "server_mcp"  # 服务端MCP
    DEVICE_IOT = "device_iot"  # 设备端IoT
    DEVICE_MCP = "device_mcp"  # 设备端MCP
    MCP_ENDPOINT = "mcp_endpoint"  # MCP接入点


@dataclass
class ToolDefinition:
    """工具定义"""

    name: str  # 工具名称
    description: Dict[str, Any]  # 工具描述（OpenAI函数调用格式）
    tool_type: ToolType  # 工具类型
    parameters: Optional[Dict[str, Any]] = None  # 额外参数
