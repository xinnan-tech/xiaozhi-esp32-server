from config.logger import setup_logging
from enum import Enum

TAG = __name__

logger = setup_logging()


class ToolType(Enum):
    NONE = (1, "调用完工具后，不做其他操作")
    WAIT = (2, "调用工具，等待函数返回")
    CHANGE_SYS_PROMPT = (3, "修改系统提示词，切换角色性格或职责")
    SYSTEM_CTL = (
        4,
        "系统控制，影响正常的对话流程，如退出、播放音乐等，需要传递conn参数",
    )
    IOT_CTL = (5, "IOT设备控制，需要传递conn参数")
    MCP_CLIENT = (6, "MCP客户端")

    def __init__(self, code, message):
        self.code = code
        self.message = message


class Action(Enum):
    ERROR = (-1, "错误")
    NOTFOUND = (0, "没有找到函数")
    NONE = (1, "啥也不干")
    RESPONSE = (2, "直接回复")
    REQLLM = (3, "调用函数后再请求llm生成回复")

    def __init__(self, code, message):
        self.code = code
        self.message = message


class ActionResponse:
    def __init__(self, action: Action, result, response):
        self.action = action  # 动作类型
        self.result = result  # 动作产生的结果
        self.response = response  # 直接回复的内容


class FunctionItem:
    def __init__(self, name, description, func, type):
        self.name = name
        self.description = description
        self.func = func
        self.type = type


class DeviceTypeRegistry:
    """设备类型注册表，用于管理IOT设备类型及其函数"""

    def __init__(self):
        self.type_functions = {}  # type_signature -> {func_name: FunctionItem}

    def generate_device_type_id(self, descriptor):
        """通过设备能力描述生成类型ID"""
        properties = sorted(descriptor["properties"].keys())
        methods = sorted(descriptor["methods"].keys())
        # 使用属性和方法的组合作为设备类型的唯一标识
        type_signature = (
            f"{descriptor['name']}:{','.join(properties)}:{','.join(methods)}"
        )
        return type_signature

    def get_device_functions(self, type_id):
        """获取设备类型对应的所有函数"""
        return self.type_functions.get(type_id, {})

    def register_device_type(self, type_id, functions):
        """注册设备类型及其函数"""
        if type_id not in self.type_functions:
            self.type_functions[type_id] = functions


# 初始化函数注册字典
all_function_registry = {}
device_type_registry = DeviceTypeRegistry()


def register_function(name, desc, type=None):
    """注册函数到函数注册字典的装饰器"""

    def decorator(func):
        all_function_registry[name] = FunctionItem(name, desc, func, type)
        logger.bind(tag=TAG).debug(f"函数 '{name}' 已加载，可以注册使用")
        return func

    return decorator


class FunctionRegistry:
    def __init__(self):
        self.function_registry = {}
        self.logger = setup_logging()

    def register_function(self, name):
        # 查找all_function_registry中是否有对应的函数
        func = all_function_registry.get(name)
        if not func:
            self.logger.bind(tag=TAG).error(f"函数 '{name}' 未找到")
            return None
        self.function_registry[name] = func
        self.logger.bind(tag=TAG).debug(f"函数 '{name}' 注册成功")
        return func

    def unregister_function(self, name):
        # 注销函数，检测是否存在
        if name not in self.function_registry:
            self.logger.bind(tag=TAG).error(f"函数 '{name}' 未找到")
            return False
        self.function_registry.pop(name, None)
        self.logger.bind(tag=TAG).info(f"函数 '{name}' 注销成功")
        return True

    def get_function(self, name):
        return self.function_registry.get(name)

    def get_all_functions(self):
        return self.function_registry

    def get_all_function_desc(self):
        return [func.description for _, func in self.function_registry.items()]
