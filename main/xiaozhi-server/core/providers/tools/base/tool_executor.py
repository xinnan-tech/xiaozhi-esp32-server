"""工具执行器基类定义"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from .tool_types import ToolDefinition
from plugins_func.register import ActionResponse


class ToolExecutor(ABC):
    """工具执行器抽象基类"""

    @abstractmethod
    async def execute(
        self, conn, tool_name: str, arguments: Dict[str, Any]
    ) -> ActionResponse:
        """执行工具调用"""
        pass

    @abstractmethod
    def get_tools(self) -> Dict[str, ToolDefinition]:
        """获取该执行器管理的所有工具"""
        pass

    @abstractmethod
    def has_tool(self, tool_name: str) -> bool:
        """检查是否有指定工具"""
        pass
