from plugins_func.register import register_function, ToolType, ActionResponse, Action
from plugins_func.functions.hass_init import initialize_hass_handler
from config.logger import setup_logging
import asyncio
import requests

TAG = __name__
logger = setup_logging()

hass_get_state_function_desc = {
    "type": "function",
    "function": {
        "name": "hass_get_state",
        "description": "获取homeassistant里设备的状态,包括灯光亮度,媒体播放器的音量,设备的暂停、继续操作",
        "parameters": {
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "需要操作的设备id,homeassistant里的entity_id"
                }
            },
            "required": ["entity_id"]
        }
    }
}


@register_function("hass_get_state", hass_get_state_function_desc, ToolType.SYSTEM_CTL)
def hass_get_state(conn, entity_id=''):
    try:

        future = asyncio.run_coroutine_threadsafe(
            handle_hass_get_state(conn, entity_id),
            conn.loop
        )
        ha_response = future.result()
        return ActionResponse(action=Action.REQLLM, result="执行成功", response=ha_response)
    except Exception as e:
        logger.bind(tag=TAG).error(f"处理设置属性意图错误: {e}")


async def handle_hass_get_state(conn, entity_id):
    HASS_CACHE = initialize_hass_handler(conn)
    api_key = HASS_CACHE['api_key']
    base_url = HASS_CACHE['base_url']
    url = f"{base_url}/api/states/{entity_id}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()['state']
    else:
        return f"切换失败，错误码: {response.status_code}"
