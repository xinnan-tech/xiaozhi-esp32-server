from plugins_func.register import register_function,ToolType, ActionResponse, Action
from config.logger import setup_logging
import asyncio

TAG = __name__
logger = setup_logging()

hass_set_state_function_desc ={
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
                                    "type":{
                                        "type":"string",
                                        "description":"需要操作的动作,打开设备:turn_on,关闭设备:turn_off,增加亮度:brightness_up,降低亮度:brightness_down,设置亮度:brightness_value,增加>音量:,volume_up降低音量:volume_down,设置音量:volume_set,设备暂停:pause,设备继续:continue,静音/取消静音:volume_mute"
                                    },
                                    "input":{
                                        "type":"int",
                                        "description": "只有在设置音量,设置亮度时候才需要,有效值为1-100,对应音量和亮度的1%-100%"
                                    },
                                    "is_muted":{
                                        "type":"string",
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
        conn.hass_handler.hass_set_state(conn, entity_id, state),
        conn.loop
      )
      ha_response = future.result()
      return ActionResponse(action=Action.REQLLM, result="执行成功", response=ha_response)
    except Exception as e:
      logger.bind(tag=TAG).error(f"处理设置属性意图错误: {e}")
