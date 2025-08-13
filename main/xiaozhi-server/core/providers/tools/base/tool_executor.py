"""Tool executor base class definition"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from .tool_types import ToolDefinition
from plugins_func.register import ActionResponse

class ToolExecutor(ABC):
    """Tool executor abstract base class"""
    
    @abstractmethod
    async def execute(
        self, conn, tool_name: str, arguments: Dict[str, Any]
    ) -> ActionResponse:
        """Execute tool call"""
        pass
    
    @abstractmethod
    def get_tools(self) -> Dict[str, ToolDefinition]:
        """Get all tools managed by this executor"""
        pass
    
    @abstractmethod
    def has_tool(self, tool_name: str) -> bool:
        """Check if specified tool exists"""
        pass
