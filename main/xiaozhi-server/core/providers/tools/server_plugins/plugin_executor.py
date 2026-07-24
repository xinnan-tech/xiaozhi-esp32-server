"""服务端插件工具执行器"""

import asyncio
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler
from ..base import ToolType, ToolDefinition, ToolExecutor
from plugins_func.register import all_function_registry, module_func_map, Action, ActionResponse


class ServerPluginExecutor(ToolExecutor):
    """服务端插件工具执行器"""

    def __init__(self, conn: "ConnectionHandler"):
        self.conn = conn
        self.config = conn.config

    async def execute(
        self, conn: "ConnectionHandler", tool_name: str, arguments: Dict[str, Any]
    ) -> ActionResponse:
        """执行服务端插件工具"""
        func_item = all_function_registry.get(tool_name)
        if not func_item:
            return ActionResponse(
                action=Action.NOTFOUND, response=f"插件函数 {tool_name} 不存在"
            )

        try:
            # 根据工具类型决定如何调用
            if hasattr(func_item, "type"):
                func_type = func_item.type
                if func_type.code in [4, 5]:  # SYSTEM_CTL, IOT_CTL (需要conn参数)
                    result = func_item.func(conn, **arguments)
                elif func_type.code == 2:  # WAIT
                    result = func_item.func(**arguments)
                elif func_type.code == 3:  # CHANGE_SYS_PROMPT
                    result = func_item.func(conn, **arguments)
                else:
                    result = func_item.func(**arguments)
            else:
                # 默认不传conn参数
                result = func_item.func(**arguments)

            # 兼容 async def 工具函数
            if asyncio.iscoroutine(result):
                result = await result

            return result

        except Exception as e:
            return ActionResponse(
                action=Action.ERROR,
                response=str(e),
            )

    def _expand_plugin_names(self, config_functions):
        """将模块级别的插件名展开为具体函数名。

        在一个 function 文件中可能注册多个 @register_function，
        配置中如果使用的是模块名（文件名），需要展开为具体的函数名列表。
        """
        if not isinstance(config_functions, list):
            try:
                config_functions = list(config_functions)
            except TypeError:
                return []

        expanded = []
        for name in config_functions:
            if name in all_function_registry:
                # 精确匹配函数名，直接保留
                expanded.append(name)
            elif name in module_func_map:
                # 模块名，展开为该模块下所有注册函数名
                expanded.extend(module_func_map[name])
            else:
                # 未知名称，保留原值（可能是 MCP 或其他工具）
                expanded.append(name)
        return expanded

    def _get_plugin_description(self, func_name):
        """获取插件函数的描述，优先精确匹配函数名，其次匹配模块名。"""
        plugins = self.config.get("plugins", {})
        # 精确匹配函数名
        if func_name in plugins:
            return plugins[func_name].get("description", "")
        # 通过 module_func_map 反向查找模块名
        for module_name, func_names in module_func_map.items():
            if func_name in func_names and module_name in plugins:
                return plugins[module_name].get("description", "")
        return ""

    def get_tools(self) -> Dict[str, ToolDefinition]:
        """获取所有注册的服务端插件工具"""
        tools = {}

        # 获取必要的函数
        necessary_functions = ["handle_exit_intent", "get_lunar"]

        # 获取配置中的函数
        config_functions = self.config["Intent"][
            self.config["selected_module"]["Intent"]
        ].get("functions", [])

        # 将模块级别的插件名展开为具体函数名（兜底机制）
        config_functions = self._expand_plugin_names(config_functions)

        # 合并所有需要的函数
        all_required_functions = list(set(necessary_functions + config_functions))

        for func_name in all_required_functions:
            func_item = all_function_registry.get(func_name)
            if func_item:
                # 从函数注册中获取描述（支持模块名和函数名的双层查找）
                fun_description = self._get_plugin_description(func_name)
                if fun_description is not None and len(fun_description) > 0:
                    if "function" in func_item.description and isinstance(
                        func_item.description["function"], dict
                    ):
                        func_item.description["function"][
                            "description"
                        ] = fun_description

                # 新闻插件：根据配置更新新闻源参数描述
                if func_name == "get_news_from_newsnow":
                    self._init_news_source_description(func_item, func_name)

                tools[func_name] = ToolDefinition(
                    name=func_name,
                    description=func_item.description,
                    tool_type=ToolType.SERVER_PLUGIN,
                )

        return tools

    def has_tool(self, tool_name: str) -> bool:
        """检查是否有指定的服务端插件工具"""
        return tool_name in all_function_registry

    def _init_news_source_description(self, func_item, func_name):
        """根据连接配置初始化新闻工具的参数描述"""
        news_sources = (
            self.config.get("plugins", {})
            .get(func_name, {})
            .get("news_sources", "")
        )
        if not news_sources:
            news_sources = "澎湃新闻;百度热搜;财联社"
        sources_str = news_sources.replace(";", "、")
        try:
            func_item.description["function"]["parameters"]["properties"]["source"][
                "description"
            ] = f"新闻源的标准中文名称，例如{sources_str}等。可选参数，如果不提供则使用默认新闻源"
        except (KeyError, TypeError):
            pass
