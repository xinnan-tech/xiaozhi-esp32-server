from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from core.handle.iotHandle import get_iot_status, send_iot_conn
import asyncio

TAG = __name__
logger = setup_logging()

async def _get_device_status(conn, device_name, device_type, property_name):
    """获取设备状态"""
    status = await get_iot_status(conn, device_type, property_name)
    if status is None:
        raise Exception(f"你的设备不支持{device_name}控制")
    return status

async def _set_device_property(conn, device_name, device_type, method_name, property_name, new_value=None, action=None, step=10):
    """设置设备属性"""
    current_value = await _get_device_status(conn, device_name, device_type, property_name)

    if action == 'raise':
        current_value += step
    elif action == 'lower':
        current_value -= step
    elif action == 'set':
        if new_value is None:
            raise Exception(f"缺少{property_name}参数")
        current_value = new_value

    # 限制属性范围在0到100之间
    current_value = max(0, min(100, current_value))

    await send_iot_conn(conn, device_type, method_name, {property_name: current_value})
    return current_value

def _handle_device_action(conn, func, success_message, error_message, *args, **kwargs):
    """处理设备操作的通用函数"""
    future = asyncio.run_coroutine_threadsafe(func(conn, *args, **kwargs), conn.loop)
    try:
        result = future.result()
        logger.bind(tag=TAG).info(f"{success_message}: {result}")
        response = f"{success_message}{result}"
        return ActionResponse(action=Action.RESPONSE, result=result, response=response)
    except Exception as e:
        logger.bind(tag=TAG).error(f"{error_message}: {e}")
        response = f"{error_message}: {e}"
        return ActionResponse(action=Action.RESPONSE, result=None, response=response)

# 设备控制
handle_device_function_desc = {
    "type": "function",
    "function": {
        "name": "handle_device",
        "description": (
            "用户想要获取或者设置设备的音量/亮度大小，或者用户觉得声音/亮度过高或过低，或者用户想提高或降低音量/亮度。"
            "比如用户说现在亮度多少，参数为：device_type:Backlight,action:get。"
            "比如用户说设置音量为50，参数为：device_type:Speaker,action:set,value:50。"
            "比如用户说亮度太高了，参数为：device_type:Backlight,action:lower。"
            "比如用户说调大音量，参数为：device_type:Speaker,action:raise。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "device_type": {
                    "type": "string",
                    "description": "设备类型，可选值：Speaker(音量),Backlight(亮度)"
                },
                "action": {
                    "type": "string",
                    "description": "动作名称，可选值：get(获取),set(设置),raise(提高),lower(降低)"
                },
                "value": {
                    "type": "integer",
                    "description": "值大小，可选值：0-100之间的整数"
                }
            },
            "required": ["device_type", "action"]
        }
    }
}

@register_function('handle_device', handle_device_function_desc, ToolType.IOT_CTL)
def handle_device(conn, device_type: str, action: str, value: int = None):
    if device_type == "Speaker":
        method_name, property_name, device_name = "SetVolume", "volume", "音量"
    elif device_type == "Backlight":
        method_name, property_name, device_name = "SetBrightness", "brightness", "亮度"
    else:
        raise Exception(f"未识别的设备类型: {device_type}")
    
    if action not in ["get", "set", "raise", "lower"]:
        raise Exception(f"未识别的动作名称: {action}")
    
    if action == "get":
        # get
        return _handle_device_action(
            conn, _get_device_status, f"当前{device_name}", f"获取{device_name}失败",
            device_name=device_name, device_type=device_type, property_name=property_name,
        )
    else:
        # set, raise, lower
        return _handle_device_action(
            conn, _set_device_property, f"{device_name}已调整到", f"{device_name}调整失败",
            device_name=device_name, device_type=device_type, method_name=method_name,
            property_name=property_name, new_value=value, action=action
        )
