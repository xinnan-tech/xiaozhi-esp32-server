"""
向后兼容模块 - plugins_func 包

此模块提供向后兼容，允许旧代码继续使用 plugins_func 路径
实际功能已迁移到 plugins 包
"""

# 从新路径导入所有内容
from plugins.register import (
    register_function,
    register_device_function,
    ToolType,
    Action,
    ActionResponse,
    FunctionItem,
    DeviceTypeRegistry,
    FunctionRegistry,
    all_function_registry,
)

__all__ = [
    "register_function",
    "register_device_function",
    "ToolType",
    "Action",
    "ActionResponse",
    "FunctionItem",
    "DeviceTypeRegistry",
    "FunctionRegistry",
    "all_function_registry",
]
