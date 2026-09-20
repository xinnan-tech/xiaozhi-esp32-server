"""
统一插件系统

该模块提供统一的插件扫描和注册机制，支持：
1. 动态拦截插件（BasePlugin子类）
2. MCP函数插件（@register_function装饰器）
3. 插件子目录结构（支持配置文件和辅助模块）
"""

import os
import sys
import importlib
import importlib.util
from typing import Optional

# 简单的日志记录，避免依赖 loguru
class SimpleLogger:
    def __init__(self, tag):
        self.tag = tag

    def info(self, msg):
        print(f"[INFO] [{self.tag}] {msg}")

    def warning(self, msg):
        print(f"[WARNING] [{self.tag}] {msg}")

    def error(self, msg):
        print(f"[ERROR] [{self.tag}] {msg}")

    def bind(self, tag):
        return SimpleLogger(tag)

TAG = __name__
logger = SimpleLogger(TAG)

# 导出常用类和函数，方便插件开发
from .base import BasePlugin, PluginAction
from .register import register_function, ToolType, ActionResponse, Action
from .manager import PluginManager

__all__ = [
    "BasePlugin",
    "PluginAction",
    "register_function",
    "ToolType",
    "ActionResponse",
    "Action",
    "PluginManager",
    "scan_plugins",
    "register_plugins_to_conn",
]


def _is_plugin_module(dirname: str) -> bool:
    """判断目录是否为插件模块"""
    # 跳过特殊目录
    if dirname.startswith("_") or dirname.startswith("."):
        return False
    # 跳过已知的非插件目录
    if dirname in ["__pycache__", "functions"]:
        return False
    return True


def _scan_plugin_directory(plugin_root: str) -> list:
    """
    扫描插件目录，返回所有需要导入的模块路径

    Args:
        plugin_root: 插件根目录路径

    Returns:
        模块路径列表，如 ['plugins.preprocess_plugin', 'plugins.my_plugin']
    """
    modules_to_import = []

    if not os.path.exists(plugin_root):
        return modules_to_import

    # 遍历插件根目录
    for item in os.listdir(plugin_root):
        item_path = os.path.join(plugin_root, item)

        # 只处理目录
        if not os.path.isdir(item_path):
            continue

        if not _is_plugin_module(item):
            continue

        # 检查目录中是否有 __init__.py
        init_file = os.path.join(item_path, "__init__.py")
        if os.path.exists(init_file):
            module_name = f"plugins.{item}"
            modules_to_import.append(module_name)

    return modules_to_import


def _import_module_safe(module_name: str) -> bool:
    """安全地导入模块"""
    try:
        importlib.import_module(module_name)
        logger.bind(tag=TAG).info(f"已加载插件模块: {module_name}")
        return True
    except Exception as e:
        logger.bind(tag=TAG).warning(f"加载插件模块 {module_name} 失败: {e}")
        return False


def scan_plugins() -> list:
    """
    扫描并导入 plugins/ 目录下的所有插件

    该函数会：
    1. 扫描 plugins/ 下的所有子目录
    2. 导入每个子目录的 __init__.py
    3. 触发 @register_function 装饰器注册
    4. 触发 BasePlugin 子类的定义（后续通过 register_plugins_to_conn 注册）

    Returns:
        成功加载的模块列表
    """
    # 获取 plugins 目录路径
    plugins_dir = os.path.dirname(os.path.abspath(__file__))

    # 扫描插件目录
    modules = _scan_plugin_directory(plugins_dir)

    # 导入所有插件模块
    loaded_modules = []
    for module_name in modules:
        if _import_module_safe(module_name):
            loaded_modules.append(module_name)

    # 兼容旧的扁平 functions 目录
    functions_dir = os.path.join(plugins_dir, "functions")
    if os.path.exists(functions_dir):
        # 使用 loadplugins 的逻辑导入 functions
        try:
            from . import loadplugins
            loadplugins.auto_import_modules("plugins.functions")
            logger.bind(tag=TAG).info("已加载 functions 目录下的MCP函数")
        except Exception as e:
            logger.bind(tag=TAG).warning(f"加载 functions 目录失败: {e}")

    logger.bind(tag=TAG).info(f"插件扫描完成，共加载 {len(loaded_modules)} 个插件模块")
    return loaded_modules


def register_plugins_to_conn(conn):
    """
    将已扫描的插件注册到连接的 plugin_manager

    这个函数应该在 connection 初始化时调用

    Args:
        conn: ConnectionHandler 实例
    """
    if not hasattr(conn, 'plugin_manager'):
        logger.bind(tag=TAG).warning("连接对象没有 plugin_manager 属性")
        return

    # 获取所有已导入的模块
    import sys

    # 查找 plugins 包中已加载的模块
    plugins_modules = [
        name for name in sys.modules.keys()
        if name.startswith("plugins.") and not name.startswith("plugins.functions")
    ]

    registered_count = 0

    for module_name in plugins_modules:
        try:
            module = sys.modules.get(module_name)
            if not module:
                continue

            # 查找模块中的 BasePlugin 子类
            for attr_name in dir(module):
                attr = getattr(module, attr_name)

                # 检查是否是 BasePlugin 的子类且不是 BasePlugin 本身
                if (isinstance(attr, type) and
                    issubclass(attr, BasePlugin) and
                    attr != BasePlugin):

                    # 创建实例并注册
                    try:
                        plugin_instance = attr(logger=conn.logger if hasattr(conn, 'logger') else None)
                        conn.plugin_manager.register_plugin(plugin_instance)
                        logger.bind(tag=TAG).info(
                            f"已注册拦截插件: {plugin_instance.name} (来自 {module_name})"
                        )
                        registered_count += 1
                    except Exception as e:
                        logger.bind(tag=TAG).error(
                            f"注册插件 {attr_name} 失败: {e}"
                        )
        except Exception as e:
            logger.bind(tag=TAG).error(f"处理模块 {module_name} 时出错: {e}")

    logger.bind(tag=TAG).info(f"插件注册完成，共注册 {registered_count} 个拦截插件")


# 向后兼容：导入旧路径的类
try:
    from .register import all_function_registry
    __all__.append("all_function_registry")
except ImportError:
    pass
