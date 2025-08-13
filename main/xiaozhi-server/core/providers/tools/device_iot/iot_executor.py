"""Device-side IoT tool executor"""

import json
import asyncio
from typing import Dict, Any
from ..base import ToolType, ToolDefinition, ToolExecutor
from plugins_func.register import Action, ActionResponse

class DeviceIoTExecutor(ToolExecutor):
    """Device-side IoT tool executor"""
    
    def __init__(self, conn):
        self.conn = conn
        self.iot_tools: Dict[str, ToolDefinition] = {}

    async def execute(
        self, conn, tool_name: str, arguments: Dict[str, Any]
    ) -> ActionResponse:
        """Execute device-side IoT tool"""
        if not self.has_tool(tool_name):
            return ActionResponse(
                action=Action.NOTFOUND, response=f"IoT tool {tool_name} does not exist"
            )

        try:
            # Parse tool name to get device name and operation type
            if tool_name.startswith("get_"):
                # Query operation: get_devicename_property
                parts = tool_name.split("_", 2)
                if len(parts) >= 3:
                    device_name = parts[1]
                    property_name = parts[2]
                    value = await self._get_iot_status(device_name, property_name)
                    
                    if value is not None:
                        # Process response template
                        response_success = arguments.get(
                            "response_success", "Query successful: {value}"
                        )
                        response = response_success.replace("{value}", str(value))
                        return ActionResponse(
                            action=Action.RESPONSE,
                            response=response,
                        )
                    else:
                        response_failure = arguments.get(
                            "response_failure", f"Unable to get status of {device_name}"
                        )
                        return ActionResponse(
                            action=Action.ERROR, response=response_failure
                        )
            else:
                # Control operation: devicename_method
                parts = tool_name.split("_", 1)
                if len(parts) >= 2:
                    device_name = parts[0]
                    method_name = parts[1]
                    
                    # Extract control parameters (exclude response parameters)
                    control_params = {
                        k: v
                        for k, v in arguments.items()
                        if k not in ["response_success", "response_failure"]
                    }
                    
                    # Send IoT control command
                    await self._send_iot_command(
                        device_name, method_name, control_params
                    )
                    
                    # Wait for status update
                    await asyncio.sleep(0.1)
                    response_success = arguments.get("response_success", "Operation successful")
                    
                    # Handle placeholders in response
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

            return ActionResponse(action=Action.ERROR, response="Unable to parse IoT tool name")

        except Exception as e:
            response_failure = arguments.get("response_failure", "Operation failed")
            return ActionResponse(action=Action.ERROR, response=response_failure)

    async def _get_iot_status(self, device_name: str, property_name: str):
        """Get IoT device status"""
        for key, value in self.conn.iot_descriptors.items():
            if key.lower() == device_name.lower():
                for property_item in value.properties:
                    if property_item["name"].lower() == property_name.lower():
                        return property_item["value"]
        return None

    async def _send_iot_command(
        self, device_name: str, method_name: str, parameters: Dict[str, Any]
    ):
        """Send IoT control command"""
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
        
        raise Exception(f"Method {method_name} not found for device {device_name}")

    def register_iot_tools(self, descriptors: list):
        """Register IoT tools"""
        for descriptor in descriptors:
            device_name = descriptor["name"]
            device_desc = descriptor["description"]
            
            # Register query tools
            if "properties" in descriptor:
                for prop_name, prop_info in descriptor["properties"].items():
                    tool_name = f"get_{device_name.lower()}_{prop_name.lower()}"
                    tool_desc = {
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "description": f"Query {prop_info['description']} of {device_desc}",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "response_success": {
                                        "type": "string",
                                        "description": f"Friendly reply when query is successful, must use {{value}} as placeholder to represent the queried value",
                                    },
                                    "response_failure": {
                                        "type": "string",
                                        "description": f"Friendly reply when query fails",
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

            # Register control tools
            if "methods" in descriptor:
                for method_name, method_info in descriptor["methods"].items():
                    tool_name = f"{device_name.lower()}_{method_name.lower()}"
                    
                    # Build parameters
                    parameters = {}
                    required_params = []
                    
                    # Add original method parameters
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
                    
                    # Add response parameters
                    parameters.update(
                        {
                            "response_success": {
                                "type": "string",
                                "description": "Friendly reply when operation is successful",
                            },
                            "response_failure": {
                                "type": "string",
                                "description": "Friendly reply when operation fails",
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
        """Get all device-side IoT tools"""
        return self.iot_tools.copy()

    def has_tool(self, tool_name: str) -> bool:
        """Check if the specified device-side IoT tool exists"""
        return tool_name in self.iot_tools