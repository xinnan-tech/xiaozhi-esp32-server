"""
向后兼容模块 - plugins_func.loadplugins

此模块提供向后兼容，实际从 plugins.loadplugins 导入
"""

from plugins.loadplugins import auto_import_modules

__all__ = ["auto_import_modules"]
