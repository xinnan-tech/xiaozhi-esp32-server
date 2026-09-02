"""Type definitions for the tool system"""

from enum import Enum

from dataclasses import dataclass
from typing import Any, Dict, Optional
from plugins_func.register import Action


class ToolType(Enum):
    """Tool type enumeration"""

    SERVER_PLUGIN = "server_plugin"  # Server Plugin
    SERVER_MCP = "server_mcp"  # Server MCP
    DEVICE_IOT = "device_iot"  # Device IoT
    DEVICE_MCP = "device_mcp"  # Device MCP
    MCP_ENDPOINT = "mcp_endpoint"  # MCP Endpoint


@dataclass
class ToolDefinition:
    """Tool definition"""

    name: str  # Tool name
    description: Dict[str, Any]  # Tool description (OpenAI function definition format)
    tool_type: ToolType  # Tool type
    parameters: Optional[Dict[str, Any]] = None  # Extra parameters
