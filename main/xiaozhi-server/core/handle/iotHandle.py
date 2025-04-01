import json
import asyncio
from config.logger import setup_logging
from plugins_func.register import (
    device_type_registry,
    register_function,
    ActionResponse,
    Action,
    ToolType,
)

TAG = __name__
logger = setup_logging()


def wrap_async_function(async_func):
    """包装异步函数为同步函数"""

    def wrapper(*args, **kwargs):
        try:
            # 获取连接对象（第一个参数）
            conn = args[0]
            if not hasattr(conn, "loop"):
                logger.bind(tag=TAG).error("Connection对象没有loop属性")
                return ActionResponse(
                    Action.ERROR,
                    "Connection对象没有loop属性",
                    "执行操作时出错: Connection对象没有loop属性",
                )

            # 使用conn对象中的事件循环
            loop = conn.loop
            # 在conn的事件循环中运行异步函数
            future = asyncio.run_coroutine_threadsafe(async_func(*args, **kwargs), loop)
            # 等待结果返回
            return future.result()
        except Exception as e:
            logger.bind(tag=TAG).error(f"运行异步函数时出错: {e}")
            return ActionResponse(Action.ERROR, str(e), f"执行操作时出错: {e}")

    return wrapper


def create_iot_function(device_name, method_name, method_info):
    """
    根据IOT设备描述生成通用的控制函数
    """

    async def iot_control_function(
        conn, response_success=None, response_failure=None, **params
    ):
        try:
            # 打印响应参数
            logger.bind(tag=TAG).info(
                f"控制函数接收到的响应参数: success='{response_success}', failure='{response_failure}'"
            )

            # 发送控制命令
            await send_iot_conn(conn, device_name, method_name, params)
            # 等待一小段时间让状态更新
            await asyncio.sleep(0.1)

            # 生成结果信息
            result = f"{device_name}的{method_name}操作执行成功"

            # 处理响应中可能的占位符
            response = response_success
            # 替换{value}占位符
            for param_name, param_value in params.items():
                # 先尝试直接替换参数值
                if "{" + param_name + "}" in response:
                    response = response.replace(
                        "{" + param_name + "}", str(param_value)
                    )

                # 如果有{value}占位符，用相关参数替换
                if "{value}" in response:
                    response = response.replace("{value}", str(param_value))
                    break

            return ActionResponse(Action.RESPONSE, result, response)
        except Exception as e:
            logger.bind(tag=TAG).error(f"执行{device_name}的{method_name}操作失败: {e}")

            # 操作失败时使用大模型提供的失败响应
            response = response_failure

            return ActionResponse(Action.ERROR, str(e), response)

    return wrap_async_function(iot_control_function)


def create_iot_query_function(device_name, prop_name, prop_info):
    """
    根据IOT设备属性创建查询函数
    """

    async def iot_query_function(conn, response_success=None, response_failure=None):
        try:
            # 打印响应参数
            logger.bind(tag=TAG).info(
                f"查询函数接收到的响应参数: success='{response_success}', failure='{response_failure}'"
            )

            value = await get_iot_status(conn, device_name, prop_name)

            # 查询成功，生成结果
            if value is not None:
                # 使用大模型提供的成功响应，并替换其中的占位符
                response = response_success.replace("{value}", str(value))

                return ActionResponse(Action.RESPONSE, str(value), response)
            else:
                # 查询失败，使用大模型提供的失败响应
                response = response_failure

                return ActionResponse(Action.ERROR, f"属性{prop_name}不存在", response)
        except Exception as e:
            logger.bind(tag=TAG).error(f"查询{device_name}的{prop_name}时出错: {e}")

            # 查询出错时使用大模型提供的失败响应
            response = response_failure

            return ActionResponse(Action.ERROR, str(e), response)

    return wrap_async_function(iot_query_function)


class IotDescriptor:
    """
    A class to represent an IoT descriptor.
    """

    def __init__(self, name, description, properties, methods):
        self.name = name
        self.description = description
        self.properties = []
        self.methods = []

        # 根据描述创建属性
        for key, value in properties.items():
            property_item = globals()[key] = {}
            property_item["name"] = key
            property_item["description"] = value["description"]
            if value["type"] == "number":
                property_item["value"] = 0
            elif value["type"] == "boolean":
                property_item["value"] = False
            else:
                property_item["value"] = ""
            self.properties.append(property_item)

        # 根据描述创建方法
        for key, value in methods.items():
            method = globals()[key] = {}
            method["description"] = value["description"]
            method["name"] = key
            for k, v in value["parameters"].items():
                method[k] = {}
                method[k]["description"] = v["description"]
                if v["type"] == "number":
                    method[k]["value"] = 0
                elif v["type"] == "boolean":
                    method[k]["value"] = False
                else:
                    method[k]["value"] = ""
            self.methods.append(method)


def register_device_type(descriptor):
    """注册设备类型及其功能"""
    device_name = descriptor["name"]
    type_id = device_type_registry.generate_device_type_id(descriptor)

    # 如果该类型已注册，直接返回类型ID
    if type_id in device_type_registry.type_functions:
        return type_id

    functions = {}

    # 为每个属性创建查询函数
    for prop_name, prop_info in descriptor["properties"].items():
        func_name = f"get_{device_name.lower()}_{prop_name.lower()}"
        func_desc = {
            "type": "function",
            "function": {
                "name": func_name,
                "description": f"查询{descriptor['description']}的{prop_info['description']}",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "response_success": {
                            "type": "string",
                            "description": f"查询成功时的友好回复，必须使用{{value}}作为占位符表示查询到的值",
                        },
                        "response_failure": {
                            "type": "string",
                            "description": f"查询失败时的友好回复，例如：'无法获取{device_name}的{prop_info['description']}'",
                        },
                    },
                    "required": ["response_success", "response_failure"],
                },
            },
        }
        query_func = create_iot_query_function(device_name, prop_name, prop_info)
        decorated_func = register_function(func_name, func_desc, ToolType.IOT_CTL)(
            query_func
        )
        functions[func_name] = decorated_func

    # 为每个方法创建控制函数
    for method_name, method_info in descriptor["methods"].items():
        func_name = f"{device_name.lower()}_{method_name.lower()}"

        # 创建参数字典，添加原有参数
        parameters = {
            param_name: {
                "type": param_info["type"],
                "description": param_info["description"],
            }
            for param_name, param_info in method_info["parameters"].items()
        }

        # 添加响应参数
        parameters.update(
            {
                "response_success": {
                    "type": "string",
                    "description": "操作成功时的友好回复,关于该设备的操作结果，设备名称尽量使用description中的名称",
                },
                "response_failure": {
                    "type": "string",
                    "description": "操作失败时的友好回复,关于该设备的操作结果，设备名称尽量使用description中的名称",
                },
            }
        )

        # 构建必须参数列表（原有参数 + 响应参数）
        required_params = list(method_info["parameters"].keys())
        required_params.extend(["response_success", "response_failure"])

        func_desc = {
            "type": "function",
            "function": {
                "name": func_name,
                "description": f"{descriptor['description']} - {method_info['description']}",
                "parameters": {
                    "type": "object",
                    "properties": parameters,
                    "required": required_params,
                },
            },
        }
        control_func = create_iot_function(device_name, method_name, method_info)
        decorated_func = register_function(func_name, func_desc, ToolType.IOT_CTL)(
            control_func
        )
        functions[func_name] = decorated_func

    device_type_registry.register_device_type(type_id, functions)
    return type_id


# 用于接受前端设备推送的搜索iot描述
async def handleIotDescriptors(conn, descriptors):
    wait_max_time = 5
    while conn.func_handler is None or not conn.func_handler.finish_init:
        await asyncio.sleep(1)
        wait_max_time -= 1
        if wait_max_time <= 0:
            logger.bind(tag=TAG).error("连接对象没有func_handler")
            return
    """处理物联网描述"""
    functions_changed = False

    for descriptor in descriptors:
        # 创建IOT设备描述符
        iot_descriptor = IotDescriptor(
            descriptor["name"],
            descriptor["description"],
            descriptor["properties"],
            descriptor["methods"],
        )
        conn.iot_descriptors[descriptor["name"]] = iot_descriptor

        if conn.use_function_call_mode:
            # 注册或获取设备类型
            type_id = register_device_type(descriptor)
            device_functions = device_type_registry.get_device_functions(type_id)

            # 在连接级注册设备函数
            if hasattr(conn, "func_handler"):
                for func_name in device_functions:
                    conn.func_handler.function_registry.register_function(func_name)
                    logger.bind(tag=TAG).info(
                        f"注册IOT函数到function handler: {func_name}"
                    )
                    functions_changed = True

    # 如果注册了新函数，更新function描述列表
    if functions_changed and hasattr(conn, "func_handler"):
        conn.func_handler.upload_functions_desc()
        func_names = conn.func_handler.current_support_functions()
        logger.bind(tag=TAG).info(f"设备类型: {type_id}")
        logger.bind(tag=TAG).info(
            f"更新function描述列表完成，当前支持的函数: {func_names}"
        )


async def handleIotStatus(conn, states):
    """处理物联网状态"""
    for state in states:
        for key, value in conn.iot_descriptors.items():
            if key == state["name"]:
                for property_item in value.properties:
                    for k, v in state["state"].items():
                        if property_item["name"] == k:
                            if type(v) != type(property_item["value"]):
                                logger.bind(tag=TAG).error(
                                    f"属性{property_item['name']}的值类型不匹配"
                                )
                                break
                            else:
                                property_item["value"] = v
                                logger.bind(tag=TAG).info(
                                    f"物联网状态更新: {key} , {property_item['name']} = {v}"
                                )
                            break
                break


async def get_iot_status(conn, name, property_name):
    """获取物联网状态"""
    for key, value in conn.iot_descriptors.items():
        if key == name:
            for property_item in value.properties:
                if property_item["name"] == property_name:
                    return property_item["value"]
    logger.bind(tag=TAG).warning(f"未找到设备 {name} 的属性 {property_name}")
    return None


async def set_iot_status(conn, name, property_name, value):
    """设置物联网状态"""
    for key, iot_descriptor in conn.iot_descriptors.items():
        if key == name:
            for property_item in iot_descriptor.properties:
                if property_item["name"] == property_name:
                    if type(value) != type(property_item["value"]):
                        logger.bind(tag=TAG).error(
                            f"属性{property_item['name']}的值类型不匹配"
                        )
                        return
                    property_item["value"] = value
                    logger.bind(tag=TAG).info(
                        f"物联网状态更新: {name} , {property_name} = {value}"
                    )
                    return
    logger.bind(tag=TAG).warning(f"未找到设备 {name} 的属性 {property_name}")


async def send_iot_conn(conn, name, method_name, parameters):
    """发送物联网指令"""
    for key, value in conn.iot_descriptors.items():
        if key == name:
            # 找到了设备
            for method in value.methods:
                # 找到了方法
                if method["name"] == method_name:
                    await conn.websocket.send(
                        json.dumps(
                            {
                                "type": "iot",
                                "commands": [
                                    {
                                        "name": name,
                                        "method": method_name,
                                        "parameters": parameters,
                                    }
                                ],
                            }
                        )
                    )
                    return
    logger.bind(tag=TAG).error(f"未找到方法{method_name}")
