from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from core.handle.iotHandle import get_iot_status, send_iot_conn
import asyncio

TAG = __name__
logger = setup_logging()

raise_and_lower_the_volume_function_desc = {
    "type": "function",
    "function": {
        "name": "raise_and_lower_the_volume",
        "description": "用户觉得声音过高或过低，或者用户想提高或降低音量。比如用户说太大声了，参数为：lower，比如用户说提高音量，参数为：raise",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "动作名称，要么是raise，要么是lower"
                }
            },
            "required": ["action"]
        }
    }
}


@register_function('raise_and_lower_the_volume', raise_and_lower_the_volume_function_desc, ToolType.IOT_CTL)
def raise_and_lower_the_volume(conn, action: str):
    """
    获取当前设备音量
    """

    future = asyncio.run_coroutine_threadsafe(
        _raise_and_lower_the_volume(conn, action),
        conn.loop
    )

    try:
        new_volume = future.result()  # 同步等待异步操作完成
        logger.bind(tag=TAG).info(f"音量操作完成: {new_volume}")
        response = f"音量已调整到{new_volume}"
    except Exception as e:
        logger.bind(tag=TAG).error(f"音量操作失败: {e}")
        response = f"音量调整失败: {e}"

    return ActionResponse(action=Action.RESPONSE, result="指令已接收", response=response)


async def _raise_and_lower_the_volume(conn, action):
    volume = await get_iot_status(conn, "Speaker", "volume")
    if action == 'raise':
        volume += 10
    elif action == 'lower':
        volume -= 10
    # 限制音量范围在0到100之间
    if volume < 0:
        volume = 0
    elif volume > 100:
        volume = 100
    await send_iot_conn(conn, "Speaker", "SetVolume", {"volume": volume})
    return volume
