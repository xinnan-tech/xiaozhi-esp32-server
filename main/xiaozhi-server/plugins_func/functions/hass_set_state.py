from plugins_func.register import register_function, ToolType, ActionResponse, Action
from plugins_func.functions.hass_init import initialize_hass_handler
from config.logger import setup_logging
import asyncio
import requests

TAG = __name__
logger = setup_logging()

hass_set_state_function_desc = {
    "type": "function",
    "function": {
        "name": "hass_set_state",
        "description": "设置homeassistant里设备的状态,包括开、关,调整灯光亮度,调整播放器的音量,设备的暂停、继续、静音操作",
        "parameters": {
            "type": "object",
            "properties": {
                "state": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "description": "需要操作的动作,打开设备:turn_on,关闭设备:turn_off,增加亮度:brightness_up,降低亮度:brightness_down,设置亮度:brightness_value,增加>音量:,volume_up降低音量:volume_down,设置音量:volume_set,设备暂停:pause,设备继续:continue,静音/取消静音:volume_mute"
                        },
                        "input": {
                            "type": "int",
                            "description": "只有在设置音量,设置亮度时候才需要,有效值为1-100,对应音量和亮度的1%-100%"
                        },
                        "is_muted": {
                            "type": "string",
                            "description": "只有在设置静音操作时才需要,设置静音的时候该值为true,取消静音时该值为false"
                        }
                    },
                    "required": ["type"]
                },
                "entity_id": {
                    "type": "string",
                    "description": "需要操作的设备id,homeassistant里的entity_id"
                }
            },
            "required": ["state", "entity_id"]
        }
    }
}


@register_function('hass_set_state', hass_set_state_function_desc, ToolType.SYSTEM_CTL)
def hass_set_state(conn, entity_id='', state={}):
    try:
        future = asyncio.run_coroutine_threadsafe(
            handle_hass_set_state(conn, entity_id, state),
            conn.loop
        )
        ha_response = future.result()
        return ActionResponse(action=Action.REQLLM, result="执行成功", response=ha_response)
    except Exception as e:
        logger.bind(tag=TAG).error(f"处理设置属性意图错误: {e}")


async def handle_hass_set_state(conn, entity_id, state):
    HASS_CACHE = initialize_hass_handler(conn)
    api_key = HASS_CACHE['api_key']
    base_url = HASS_CACHE['base_url']
    '''
    state = { "type":"brightness_up","input":"80","is_muted":"true"}
    '''
    domains = entity_id.split(".")
    if len(domains) > 1:
        domain = domains[0]
    else:
        return "执行失败，错误的设备id"
    action = ''
    arg = ''
    value = ''
    if state['type'] == 'turn_on':
        description = "设备已打开"
        if domain == "cover":
            action = "open_cover"
        elif domain == "vacuum":
            action = "start"
        else:
            action = "turn_on"
    elif state['type'] == 'turn_off':
        description = "设备已关闭"
        if domain == 'cover':
            action = "close_cover"
        elif domain == 'vacuum':
            action = "stop"
        else:
            action = "turn_off"
    elif state['type'] == 'brightness_up':
        description = "灯光已调亮"
        action = 'turn_on'
        arg = 'brightness_step_pct'
        value = 10
    elif state['type'] == 'brightness_down':
        description = "灯光已调暗"
        action = 'turn_on'
        arg = 'brightness_step_pct'
        value = -10
    elif state['type'] == 'brightness_value':
        description = f"亮度已调整到{state['input']}"
        action = 'turn_on'
        arg = 'brightness_pct'
        value = state['input']
    elif state['type'] == 'volume_up':
        description = "音量已调大"
        action = state['type']
    elif state['type'] == 'volume_down':
        description = "音量已调小"
        action = state['type']
    elif state['type'] == 'volume_set':
        description = f"音量已调整到{state['input']}"
        action = state['type']
        arg = 'volume_level'
        value = state['input']
    elif state['type'] == 'volume_mute':
        description = f"设备已静音"
        action = state['type']
        arg = 'is_volume_muted'
        value = state['is_muted']
    elif state['type'] == 'pause':
        description = f"设备已暂停"
        action = state['type']
        if domain == 'media_player':
            action = 'media_pause'
        if domain == 'cover':
            action = 'stop_cover'
        if domain == 'vacuum':
            action = 'pause'
    elif state['type'] == 'continue':
        description = f"设备已继续"
        if domain == 'media_player':
            action = 'media_play'
        if domain == 'vacuum':
            action = 'start'
    else:
        return f"{domain} {state.type}功能尚未支持"

    if arg == '':
        data = {
            "entity_id": entity_id,
        }
    else:
        data = {
            "entity_id": entity_id,
            arg: value
        }
    url = f"{base_url}/api/services/{domain}/{action}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    response = requests.post(url, headers=headers, json=data)
    logger.bind(tag=TAG).info(f"设置状态:url:{url},return_code:{response.status_code}")
    if response.status_code == 200:
        return description
    else:
        return f"设置失败，错误码: {response.status_code}"
