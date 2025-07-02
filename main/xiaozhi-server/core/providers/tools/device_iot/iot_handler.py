"""IoT设备支持模块，提供IoT设备描述符和状态处理"""

import asyncio
from config.logger import setup_logging
from .iot_descriptor import IotDescriptor

TAG = __name__
logger = setup_logging()


async def handleIotDescriptors(conn, descriptors):
    """处理物联网描述"""
    wait_max_time = 5
    while (
        not hasattr(conn, "func_handler")
        or conn.func_handler is None
        or not conn.func_handler.finish_init
    ):
        await asyncio.sleep(1)
        wait_max_time -= 1
        if wait_max_time <= 0:
            logger.bind(tag=TAG).debug("连接对象没有func_handler")
            return

    functions_changed = False

    for descriptor in descriptors:
        # 如果descriptor没有properties和methods，则直接跳过
        if "properties" not in descriptor and "methods" not in descriptor:
            continue

        # 处理缺失properties的情况
        if "properties" not in descriptor:
            descriptor["properties"] = {}
            # 从methods中提取所有参数作为properties
            if "methods" in descriptor:
                for method_name, method_info in descriptor["methods"].items():
                    if "parameters" in method_info:
                        for param_name, param_info in method_info["parameters"].items():
                            # 将参数信息转换为属性信息
                            descriptor["properties"][param_name] = {
                                "description": param_info["description"],
                                "type": param_info["type"],
                            }

        # 创建IOT设备描述符
        iot_descriptor = IotDescriptor(
            descriptor["name"],
            descriptor["description"],
            descriptor["properties"],
            descriptor["methods"],
        )
        conn.iot_descriptors[descriptor["name"]] = iot_descriptor
        functions_changed = True

    # 如果注册了新函数，更新function描述列表
    if functions_changed and hasattr(conn, "func_handler"):
        # 注册IoT工具到统一工具处理器
        await conn.func_handler.register_iot_tools(descriptors)

        conn.func_handler.current_support_functions()


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
