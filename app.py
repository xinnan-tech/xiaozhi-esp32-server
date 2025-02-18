import asyncio
from config.logger import setup_logging
from config.settings import load_config
from core.websocket_server import WebSocketServer
from manager.http_server import WebUI
from aiohttp import web
from core.utils.util import get_local_ip

TAG = __name__

async def main():
    logger = setup_logging()
    config = load_config()
    
    # 启动 WebSocket 服务器
    ws_server = WebSocketServer(config)
    ws_task = asyncio.create_task(ws_server.start())

    # 启动 WebUI 服务器
    webui_runner = None
    if config['manager'].get('enabled', False):
        server_config = config["manager"]
        host = server_config["ip"]
        port = server_config["port"]
        try:
            webui = WebUI()
            runner = web.AppRunner(webui.app)
            await runner.setup()
            site = web.TCPSite(runner, host, port)
            await site.start()
            webui_runner = runner
            local_ip = get_local_ip()
            logger.bind(tag=TAG).info(f"WebUI server is running at http://{local_ip}:{port}")
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to start WebUI server: {e}")
    
    try:
        # 等待 WebSocket 服务器运行
        await ws_task
    finally:
        # 清理 WebUI 服务器
        if webui_runner:
            await webui_runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
