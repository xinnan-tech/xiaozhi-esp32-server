from plugins_func.register import register_function,ToolType, ActionResponse, Action
from config.logger import setup_logging
from core.handle.musicHandler import handle_music_command
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

        # 检查事件循环状态
        if not conn.loop.is_running():
            logger.bind(tag=TAG).error("事件循环未运行，无法提交任务")
            return ActionResponse(action=Action.RESPONSE, result="系统繁忙", response="请稍后再试")

        # 提交异步任务
        future = asyncio.run_coroutine_threadsafe(
            handle_music_command(conn, music_intent),
            conn.loop
        )

        # 非阻塞回调处理
        def handle_done(f):
            try:
                f.result()  # 可在此处理成功逻辑
                logger.bind(tag=TAG).info("播放完成")
            except Exception as e:
                logger.bind(tag=TAG).error(f"播放失败: {e}")

        future.add_done_callback(handle_done)

        return ActionResponse(action=Action.RESPONSE, result="指令已接收", response="正在为您播放音乐")
    except Exception as e:
        logger.bind(tag=TAG).error(f"处理音乐意图错误: {e}")
        return ActionResponse(action=Action.RESPONSE, result=str(e), response="播放音乐时出错了")