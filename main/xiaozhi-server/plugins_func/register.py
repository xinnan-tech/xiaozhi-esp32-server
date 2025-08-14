from config.logger import setup_logging
from enum import Enum

TAG = __name__

logger = setup_logging()


class ToolType(Enum):
    NONE = (1, "No other operations after calling tool")
    WAIT = (2, "Call tool and wait for function return")
    CHANGE_SYS_PROMPT = (
        3, "Modify system prompt, switch role personality or responsibility")
    SYSTEM_CTL = (
        4,
        "System control, affects normal conversation flow, such as exit, play music, etc., requires conn parameter",
    )
    IOT_CTL = (5, "IOT device control, requires conn parameter")
    MCP_CLIENT = (6, "MCP client")

    def __init__(self, code, message):
        self.code = code
        self.message = message


class Action(Enum):
    ERROR = (-1, "Error")
    NOTFOUND = (0, "Function not found")
    NONE = (1, "Do nothing")
    RESPONSE = (2, "Direct response")
    REQLLM = (3, "Request LLM to generate response after calling function")

    def __init__(self, code, message):
        self.code = code
        self.message = message


class ActionResponse:
    def __init__(self, action: Action, result=None, response=None):
        self.action = action  # Action type
        self.result = result  # Result produced by action
        self.response = response  # Direct response content


class FunctionItem:
    def __init__(self, name, description, func, type):
        self.name = name
        self.description = description
        self.func = func
        self.type = type


class DeviceTypeRegistry:
    """Device type registry for managing IOT device types and their functions"""

    def __init__(self):
        self.type_functions = {}  # type_signature -> {func_name: FunctionItem}

    def generate_device_type_id(self, descriptor):
        """Generate type ID through device capability description"""
        properties = sorted(descriptor["properties"].keys())
        methods = sorted(descriptor["methods"].keys())
        # Use combination of properties and methods as unique identifier for device type
        type_signature = (
            f"{descriptor['name']}:{','.join(properties)}:{','.join(methods)}"
        )
        return type_signature

    def get_device_functions(self, type_id):
        """Get all functions corresponding to device type"""
        return self.type_functions.get(type_id, {})

    def register_device_type(self, type_id, functions):
        """Register device type and its functions"""
        if type_id not in self.type_functions:
            self.type_functions[type_id] = functions


# Initialize function registry dictionary
all_function_registry = {}


def register_function(name, desc, type=None):
    """Decorator for registering functions to function registry dictionary"""

    def decorator(func):
        all_function_registry[name] = FunctionItem(name, desc, func, type)
        logger.bind(tag=TAG).debug(
            f"Function '{name}' loaded, ready for registration")
        return func

    return decorator


def register_device_function(name, desc, type=None):
    """Decorator for registering device-level functions to function registry dictionary"""

    def decorator(func):
        logger.bind(tag=TAG).debug(f"Device function '{name}' loaded")
        return func

    return decorator


class FunctionRegistry:
    def __init__(self):
        self.function_registry = {}
        self.logger = setup_logging()

    def register_function(self, name, func_item=None):
        # If func_item is provided, register directly
        if func_item:
            self.function_registry[name] = func_item
            self.logger.bind(tag=TAG).debug(
                f"Function '{name}' registered directly")
            return func_item

        # Otherwise search from all_function_registry
        func = all_function_registry.get(name)
        if not func:
            self.logger.bind(tag=TAG).error(f"Function '{name}' not found")
            return None
        self.function_registry[name] = func
        self.logger.bind(tag=TAG).debug(
            f"Function '{name}' registered successfully")
        return func

    def unregister_function(self, name):
        # Unregister function, check if exists
        if name not in self.function_registry:
            self.logger.bind(tag=TAG).error(f"Function '{name}' not found")
            return False
        self.function_registry.pop(name, None)
        self.logger.bind(tag=TAG).info(
            f"Function '{name}' unregistered successfully")
        return True

    def get_function(self, name):
        return self.function_registry.get(name)

    def get_all_functions(self):
        return self.function_registry

    def get_all_function_desc(self):
        return [func.description for _, func in self.function_registry.items()]
