"""设备端IoT工具执行器"""

import json
import asyncio
from typing import Dict, Any
from ..base import ToolType, ToolDefinition, ToolExecutor
from plugins_func.register import Action, ActionResponse


class DeviceIoTExecutor(ToolExecutor):
    """设备端IoT工具执行器"""

    def __init__(self, conn):
        self.conn = conn
        self.iot_tools: Dict[str, ToolDefinition] = {}

    async def execute(
        self, conn, tool_name: str, arguments: Dict[str, Any]
    ) -> ActionResponse:
        """执行设备端IoT工具"""
        if not self.has_tool(tool_name):
            return ActionResponse(
                action=Action.NOTFOUND, response=f"IoT工具 {tool_name} 不存在"
            )

        try:
            # 解析工具名称，获取设备名和操作类型
            if tool_name.startswith("get_"):
                # 查询操作：get_devicename_property
                parts = tool_name.split("_", 2)
                if len(parts) >= 3:
                    device_name = parts[1]
                    property_name = parts[2]

                    value = await self._get_iot_status(device_name, property_name)
                    if value is not None:
                        # 处理响应模板
                        response_success = arguments.get(
                            "response_success", "查询成功：{value}"
                        )
                        response = response_success.replace("{value}", str(value))

                        return ActionResponse(
                            action=Action.RESPONSE,
                            response=response,
                        )
                    else:
                        response_failure = arguments.get(
                            "response_failure", f"无法获取{device_name}的状态"
                        )
                        return ActionResponse(
                            action=Action.ERROR, response=response_failure
                        )
            else:
                # 控制操作：devicename_method
                parts = tool_name.split("_", 1)
                if len(parts) >= 2:
                    device_name = parts[0]
                    method_name = parts[1]

                    # 提取控制参数（排除响应参数）
                    control_params = {
                        k: v
                        for k, v in arguments.items()
                        if k not in ["response_success", "response_failure"]
                    }

                    # 发送IoT控制命令
                    await self._send_iot_command(
                        device_name, method_name, control_params
                    )

                    # 等待状态更新
                    await asyncio.sleep(0.1)

                    response_success = arguments.get("response_success", "操作成功")

                    # 处理响应中的占位符
                    for param_name, param_value in control_params.items():
                        placeholder = "{" + param_name + "}"
                        if placeholder in response_success:
                            response_success = response_success.replace(
                                placeholder, str(param_value)
                            )
                        if "{value}" in response_success:
                            response_success = response_success.replace(
                                "{value}", str(param_value)
                            )
                            break

                    return ActionResponse(
                        action=Action.REQLLM,
                        result=response_success,
                    )

            return ActionResponse(action=Action.ERROR, response="无法解析IoT工具名称")

        except Exception as e:
            response_failure = arguments.get("response_failure", "操作失败")
            return ActionResponse(action=Action.ERROR, response=response_failure)

    async def _get_iot_status(self, device_name: str, property_name: str):
        """获取IoT设备状态"""
        for key, value in self.conn.iot_descriptors.items():
            if key.lower() == device_name.lower():
                for property_item in value.properties:
                    if property_item["name"].lower() == property_name.lower():
                        return property_item["value"]
        return None

    async def _send_iot_command(
        self, device_name: str, method_name: str, parameters: Dict[str, Any]
    ):
        """发送IoT控制命令"""
        for key, value in self.conn.iot_descriptors.items():
            if key.lower() == device_name.lower():
                for method in value.methods:
                    if method["name"].lower() == method_name.lower():
                        command = {
                            "name": key,
                            "method": method["name"],
                        }

                        if parameters:
                            command["parameters"] = parameters

                        send_message = json.dumps(
                            {"type": "iot", "commands": [command]}
                        )
                        await self.conn.websocket.send(send_message)
                        return

        raise Exception(f"未找到设备{device_name}的方法{method_name}")

    def register_iot_tools(self, descriptors: list):
        """注册IoT工具"""
        for descriptor in descriptors:
            device_name = descriptor["name"]
            device_desc = descriptor["description"]

            # 注册查询工具
            if "properties" in descriptor:
                for prop_name, prop_info in descriptor["properties"].items():
                    tool_name = f"get_{device_name.lower()}_{prop_name.lower()}"

                    tool_desc = {
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "description": f"查询{device_desc}的{prop_info['description']}",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "response_success": {
                                        "type": "string",
                                        "description": f"查询成功时的友好回复，必须使用{{value}}作为占位符表示查询到的值",
                                    },
                                    "response_failure": {
                                        "type": "string",
                                        "description": f"查询失败时的友好回复",
                                    },
                                },
                                "required": ["response_success", "response_failure"],
                            },
                        },
                    }

                    self.iot_tools[tool_name] = ToolDefinition(
                        name=tool_name,
                        description=tool_desc,
                        tool_type=ToolType.DEVICE_IOT,
                    )

            # 注册控制工具
            if "methods" in descriptor:
                for method_name, method_info in descriptor["methods"].items():
                    tool_name = f"{device_name.lower()}_{method_name.lower()}"

                    # 构建参数
                    parameters = {}
                    required_params = []

                    # 添加方法的原始参数
                    if "parameters" in method_info:
                        parameters.update(
                            {
                                param_name: {
                                    "type": param_info["type"],
                                    "description": param_info["description"],
                                }
                                for param_name, param_info in method_info[
                                    "parameters"
                                ].items()
                            }
                        )
                        required_params.extend(method_info["parameters"].keys())

                    # 添加响应参数
                    parameters.update(
                        {
                            "response_success": {
                                "type": "string",
                                "description": "操作成功时的友好回复",
                            },
                            "response_failure": {
                                "type": "string",
                                "description": "操作失败时的友好回复",
                            },
                        }
                    )
                    required_params.extend(["response_success", "response_failure"])

                    tool_desc = {
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "description": f"{device_desc} - {method_info['description']}",
                            "parameters": {
                                "type": "object",
                                "properties": parameters,
                                "required": required_params,
                            },
                        },
                    }

                    self.iot_tools[tool_name] = ToolDefinition(
                        name=tool_name,
                        description=tool_desc,
                        tool_type=ToolType.DEVICE_IOT,
                    )

    def get_tools(self) -> Dict[str, ToolDefinition]:
        """获取所有设备端IoT工具"""
        return self.iot_tools.copy()

    def has_tool(self, tool_name: str) -> bool:
        """检查是否有指定的设备端IoT工具"""
        return tool_name in self.iot_tools
