from plugins_func.register import register_function,ToolType, ActionResponse, Action
from config.logger import setup_logging
import asyncio

TAG = __name__
logger = setup_logging()

hass_play_music_function_desc = {
            "type": "function",
            "function": {
                "name": "hass_play_music",
                "description": "用户想听音乐、有声书的时候使用，在房间的媒体播放器（media_player）里播放对应音频",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "media_content_id": {
                                "type": "string",
                                "description": "可以是音乐或有声书的专辑名称、歌曲名、演唱者,如果未指定就填random"
                            },
                            "entity_id": {
                            "type": "string",
                            "description": "需要操作的音箱的设备id,homeassistant里的entity_id,media_player开头"
                            }
                        },
                        "required": ["media_content_id", "entity_id"]
                    }
                }
            }


@register_function('hass_play_music', hass_play_music_function_desc, ToolType.SYSTEM_CTL)
#def hass_play_music(conn, arguments):
def hass_play_music(conn, entity_id='', media_content_id='random'):
    try:
        #logger.bind(tag=TAG).error(f"arguments: {arguments}")
        
        #entity_id = arguments["entity_id"]
        #media_content_id = arguments["media_content_id"]
        
        #logger.bind(tag=TAG).error(f"entity_id: {entity_id}")


        # 执行音乐播放命令
        future = asyncio.run_coroutine_threadsafe(
            conn.hass_handler.hass_play_music(conn, entity_id, media_content_id),
            conn.loop
        )
        ha_response = future.result()
        return ActionResponse(action=Action.RESPONSE, result="退出意图已处理", response=ha_response)
    except Exception as e:
        logger.bind(tag=TAG).error(f"处理音乐意图错误: {e}")
