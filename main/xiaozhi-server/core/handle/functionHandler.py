import asyncio
from enum import Enum

from config.logger import setup_logging
import json
from plugins_func.register import FunctionRegistry, ActionResponse, Action, ToolType
TAG = __name__
logger = setup_logging()


class FunctionHandler:
    def __init__(self, config):
        self.config = config
        self.function_registry = FunctionRegistry()
        self.register_nessary_functions()
        self.register_config_functions()
        self.functions_desc = self.function_registry.get_all_function_desc()
        func_names = self.current_support_functions()
        self.modify_plugin_loader_des(func_names)

    def modify_plugin_loader_des(self, func_names):
        if "plugin_loader" not in func_names:
            return
        # 可编辑的列表中去掉plugin_loader
        surport_plugins = [func for func in func_names if func != "plugin_loader"]
        func_names = ",".join(surport_plugins)
        for function_desc in self.functions_desc:
            if function_desc["function"]["name"] == "plugin_loader":
                function_desc["function"]["description"] = function_desc["function"]["description"].replace("[plugins]", func_names)
                break
        
    def upload_functions_desc(self):
        self.functions_desc = self.function_registry.get_all_function_desc()

    def current_support_functions(self):
        func_names = []
        for func in self.functions_desc:
            func_names.append(func["function"]["name"])
        # 打印当前支持的函数列表
        logger.bind(tag=TAG).info(f"当前支持的函数列表: {func_names}")
        return func_names

    def get_functions(self):
        """获取功能调用配置"""
        return self.functions_desc

    def register_nessary_functions(self):
        """注册必要的函数"""
        self.function_registry.register_function("handle_exit_intent")
        self.function_registry.register_function("play_music")
        self.function_registry.register_function("plugin_loader")
        self.function_registry.register_function("get_time")

    def register_config_functions(self):
        """注册配置中的函数,可以不同客户端使用不同的配置"""
        for func in self.config["Intent"]["function_call"].get("functions", []):
            self.function_registry.register_function(func)

    def get_function(self, name):
        return self.function_registry.get_function(name)

    def handle_llm_function_call(self, conn, function_call_data):
        try:
            function_name = function_call_data["name"]
            funcItem = self.get_function(function_name)
            if not funcItem:
                return ActionResponse(action=Action.NOTFOUND, result="没有找到对应的函数", response="")
            func = funcItem.func
            arguments = function_call_data["arguments"]
            arguments = json.loads(arguments) if arguments else {}
            logger.bind(tag=TAG).info(f"调用函数: {function_name}, 参数: {arguments}")
            if funcItem.type == ToolType.SYSTEM_CTL:
                return func(conn, **arguments)
            elif funcItem.type == ToolType.WAIT:
                return func(**arguments)
            elif funcItem.type == ToolType.CHANGE_SYS_PROMPT:
                return func(conn, **arguments)
            else:
                return ActionResponse(action=Action.NOTFOUND, result="没有找到对应的函数", response="")
        except Exception as e:
            logger.bind(tag=TAG).error(f"处理function call错误: {e}")

        return None