from config.logger import setup_logging
import json
from plugins_func.register import (
    FunctionRegistry,
    ActionResponse,
    Action,
    ToolType,
    DeviceTypeRegistry,
)
from plugins_func.functions.hass_init import append_devices_to_prompt

TAG = __name__


class FunctionHandler:
    def __init__(self, conn):
        self.conn = conn
        self.config = conn.config
        self.device_type_registry = DeviceTypeRegistry()
        self.function_registry = FunctionRegistry()
        self.register_nessary_functions()
        self.register_config_functions()
        self.functions_desc = self.function_registry.get_all_function_desc()
        self.finish_init = True
    
    def upload_functions_desc(self):
        self.functions_desc = self.function_registry.get_all_function_desc()


    def current_support_functions(self):
        func_names = []
        for func in self.functions_desc:
            func_names.append(func["function"]["name"])
        # 打印当前支持的函数列表
        self.conn.logger.bind(tag=TAG, session_id=self.conn.session_id).info(
            f"当前支持的函数列表: {func_names}"
        )
        return func_names

    def get_functions(self):
        """获取功能调用配置"""
        return self.functions_desc

    def register_nessary_functions(self):
        """注册必要的函数"""
        self.function_registry.register_function("handle_exit_intent")
        self.function_registry.register_function("get_time")
        self.function_registry.register_function("get_lunar")

    def register_config_functions(self):
        """注册配置中的函数,可以不同客户端使用不同的配置"""
        for func in self.config["Intent"][self.config["selected_module"]["Intent"]].get(
            "functions", []
        ):
            self.function_registry.register_function(func)

        """home assistant需要初始化提示词"""
        append_devices_to_prompt(self.conn)

    def get_function(self, name):
        return self.function_registry.get_function(name)

    def handle_llm_function_call(self, conn, function_call_data):
        # 多函数调用处理
        if "function_calls" in function_call_data:
            responses = []
            for call in function_call_data["function_calls"]:
                func = self.get_function(call["name"])
                if func:
                    # 执行函数并收集响应
                    response = func(conn, **call.get("arguments", {}))
                    responses.append(response)
            return self._combine_responses(responses)  # 合并响应
        try:
            function_name = function_call_data["name"]
            funcItem = self.get_function(function_name)
            if not funcItem:
                return ActionResponse(
                    action=Action.NOTFOUND, result="没有找到对应的函数", response=""
                )
            func = funcItem.func
            arguments = function_call_data["arguments"]
            arguments = json.loads(arguments) if arguments else {}
            self.conn.logger.bind(tag=TAG).debug(
                f"调用函数: {function_name}, 参数: {arguments}"
            )
            if (
                funcItem.type == ToolType.SYSTEM_CTL
                or funcItem.type == ToolType.IOT_CTL
            ):
                return func(conn, **arguments)
            elif funcItem.type == ToolType.WAIT:
                return func(**arguments)
            elif funcItem.type == ToolType.CHANGE_SYS_PROMPT:
                return func(conn, **arguments)
            else:
                return ActionResponse(
                    action=Action.NOTFOUND, result="没有找到对应的函数", response=""
                )
        except Exception as e:
            self.conn.logger.bind(tag=TAG).error(f"处理function call错误: {e}")

        return None
