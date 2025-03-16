from plugins_func.register import register_function,ToolType, ActionResponse, Action
from config.logger import setup_logging
import asyncio

TAG = __name__
logger = setup_logging()

play_music_function_desc = {
                "type": "function",
                "function": {
                    "name": "play_music",
                    "description": "唱歌、听歌、播放音乐方法。比如用户说播放音乐，参数为：random，比如用户说播放两只老虎，参数为：两只老虎",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "song_name": {
                                "type": "string",
                                "description": "歌曲名称，如果没有指定具体歌名则为'random'"
                            }
                        },
                        "required": ["song_name"]
                    }
                }
            }


@register_function('play_music', play_music_function_desc, ToolType.SYSTEM_CTL)
def play_music(conn, song_name: str):
    try:
        music_intent = f"播放音乐 {song_name}" if song_name != "random" else "随机播放音乐"

        # 执行音乐播放命令
        future = asyncio.run_coroutine_threadsafe(
            conn.music_handler.handle_music_command(conn, music_intent),
            conn.loop
        )
        future.result()
        return ActionResponse(action=Action.RESPONSE, result="退出意图已处理", response="还想听什么歌？")
    except Exception as e:
        logger.bind(tag=TAG).error(f"处理音乐意图错误: {e}")