import asyncio
from config.settings import load_config, check_config_file
from core.websocket_server import WebSocketServer
from core.utils.util import check_ffmpeg_installed

TAG = __name__


async def main():
    check_config_file()
    check_ffmpeg_installed()
    config = load_config()

    # 启动 WebSocket 服务器
    ws_server = WebSocketServer(config)
    ws_task = asyncio.create_task(ws_server.start())

    try:
        # 等待 WebSocket 服务器运行
        await ws_task
    finally:
        ws_task.cancel()


if __name__ == "__main__":
    asyncio.run(main())
