"""
向后兼容模块 - plugins_func.register

此模块提供向后兼容，实际从 plugins.register 导入
"""

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
    module_func_map,
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
    "module_func_map",
]
