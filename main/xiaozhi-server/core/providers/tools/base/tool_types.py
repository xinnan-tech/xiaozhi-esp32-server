"""Type definitions for tool system"""

from enum import Enum
from dataclasses import dataclass
from typing import Any, Dict, Optional
from plugins_func.register import Action


class ToolType(Enum):
    """Tool type enumeration"""
    SERVER_PLUGIN = "server_plugin"  # Server-side plugin
    SERVER_MCP = "server_mcp"        # Server-side MCP
    DEVICE_IOT = "device_iot"        # Device-side IoT
    DEVICE_MCP = "device_mcp"        # Device-side MCP
    MCP_ENDPOINT = "mcp_endpoint"    # MCP endpoint


@dataclass
class ToolDefinition:
    """Tool definition"""
    name: str                                    # Tool name
    # Tool description (OpenAI function call format)
    description: Dict[str, Any]
    tool_type: ToolType                          # Tool type
    parameters: Optional[Dict[str, Any]] = None  # Additional parameters
