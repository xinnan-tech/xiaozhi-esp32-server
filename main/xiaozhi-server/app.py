import asyncio
import sys
from config.settings import load_config, check_config_file
from core.websocket_server import WebSocketServer
from core.utils.util import check_ffmpeg_installed

TAG = __name__

async def wait_for_exit():
    """在 Windows 上等待用户按 Ctrl + C"""
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, sys.stdin.read)  # 监听标准输入（阻塞）

async def main():
    check_config_file()
    check_ffmpeg_installed()
    config = load_config()

    # 启动 WebSocket 服务器
    ws_server = WebSocketServer(config)
    ws_task = asyncio.create_task(ws_server.start())

    try:
        await wait_for_exit()  # Windows 下用 sys.stdin.read() 监听退出
    except asyncio.CancelledError:
        print("任务被取消，清理资源中...")
    finally:
        ws_task.cancel()
        try:
            await ws_task  # 确保 WebSocket 任务正确关闭
        except asyncio.CancelledError:
            pass  # 忽略取消异常
        print("服务器已关闭，程序退出。")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("手动中断，程序终止。")
