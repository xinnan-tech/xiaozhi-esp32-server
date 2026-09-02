import sys
import uuid
import signal
import asyncio
from aioconsole import ainput
from config.settings import load_config
from config.logger import setup_logging
from core.utils.util import get_local_ip, validate_mcp_endpoint
from core.http_server import SimpleHttpServer
from core.websocket_server import WebSocketServer
from core.utils.util import check_ffmpeg_installed
from core.utils.gc_manager import get_gc_manager
from core.utils.npr_scraper import news_scraper_task
from core.utils.cgm_manager import cgm_background_task
from core.utils.pump_manager import create_pump_background_task

TAG = __name__
logger = setup_logging()


async def wait_for_exit() -> None:
    """
    Block until Ctrl-C / SIGTERM is received.
    - Unix: Use add_signal_handler
    - Windows: Rely on KeyboardInterrupt
    """
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    if sys.platform != "win32":  # Unix / macOS
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop_event.set)
        await stop_event.wait()
    else:
        # Windows: await a forever pending fut,
        # Let KeyboardInterrupt bubble up to asyncio.run, resolving the issue of lingering threads blocking process exit
        try:
            await asyncio.Future()
        except KeyboardInterrupt:  # Ctrl‑C
            pass


async def monitor_stdin():
    """Monitor standard input, consume enter key"""
    while True:
        await ainput()  # Asynchronously wait for input, consume enter key


async def main():
    check_ffmpeg_installed()
    config = load_config()

    # auth_key priority: config file server.auth_key > manager-api.secret > automatically generated
    # auth_key is used for jwt authentication, such as jwt authentication for vision analysis interface, ota interface token generation and websocket authentication
    # Get auth_key from config file
    auth_key = config["server"].get("auth_key", "")
    
    # Verify auth_key, if invalid try to use manager-api.secret
    if not auth_key or len(auth_key) == 0 or "你" in auth_key:
        auth_key = config.get("manager-api", {}).get("secret", "")
        # Verify secret, if invalid generate random key
        if not auth_key or len(auth_key) == 0 or "你" in auth_key:
            auth_key = str(uuid.uuid4().hex)
    
    config["server"]["auth_key"] = auth_key

    # Add stdin monitoring task
    stdin_task = asyncio.create_task(monitor_stdin())

    # Start global GC manager (clean up every 5 minutes)
    gc_manager = get_gc_manager(interval_seconds=300)
    await gc_manager.start()

    # Start NPR news scraper
    scraper_task = asyncio.create_task(news_scraper_task())
    # Start CGM scraper
    cgm_task = asyncio.create_task(cgm_background_task())
    # Start Pump scraper
    pump_task = asyncio.create_task(create_pump_background_task())
    # Start WebSocket server
    ws_server = WebSocketServer(config)
    ws_task = asyncio.create_task(ws_server.start())
    # Start Simple http server
    ota_server = SimpleHttpServer(config)
    ota_task = asyncio.create_task(ota_server.start())

    read_config_from_api = config.get("read_config_from_api", False)
    port = int(config["server"].get("http_port", 8003))
    if not read_config_from_api:
        logger.bind(tag=TAG).info(
            "OTA interface is\t\thttp://{}:{}/xiaozhi/ota/",
            get_local_ip(),
            port,
        )
    logger.bind(tag=TAG).info(
        "Vision analysis interface is\thttp://{}:{}/mcp/vision/explain",
        get_local_ip(),
        port,
    )
    mcp_endpoint = config.get("mcp_endpoint", None)
    if mcp_endpoint is not None and "你" not in mcp_endpoint:
        # Validate MCP endpoint format
        if validate_mcp_endpoint(mcp_endpoint):
            logger.bind(tag=TAG).info("MCP endpoint is\t{}", mcp_endpoint)
            # Convert mcp endpoint address to call point
            mcp_endpoint = mcp_endpoint.replace("/mcp/", "/call/")
            config["mcp_endpoint"] = mcp_endpoint
        else:
            logger.bind(tag=TAG).error("MCP endpoint is invalid")
            config["mcp_endpoint"] = "Your endpoint websocket address"

    # Get WebSocket config, use safe defaults
    websocket_port = 8000
    server_config = config.get("server", {})
    if isinstance(server_config, dict):
        websocket_port = int(server_config.get("port", 8000))

    # Determine final websocket address for logging
    final_ws_url = f"ws://{get_local_ip()}:{websocket_port}/xiaozhi/v1/"
    websocket_config = server_config.get("websocket")
    
    # Check if config is valid (using the same logic as http_server.py)
    if websocket_config:
         final_ws_url = websocket_config

    logger.bind(tag=TAG).info(
        "Websocket address is\t{}",
        final_ws_url,
    )

    logger.bind(tag=TAG).info(
        "======= The address above is a websocket protocol address, please do not access it with a browser ======="
    )
    logger.bind(tag=TAG).info(
        "If you want to test websocket, please open test_page.html in the test directory with Google Chrome"
    )
    logger.bind(tag=TAG).info(
        "=============================================================\n"
    )

    try:
        await wait_for_exit()  # Block until exit signal is received
    except asyncio.CancelledError:
        print("Task cancelled, cleaning up resources...")
    finally:
        # Stop global GC manager
        await gc_manager.stop()

        # Cancel all tasks (critical repair point)
        stdin_task.cancel()
        ws_task.cancel()
        if ota_task:
            ota_task.cancel()

        scraper_task.cancel()
        cgm_task.cancel()
        pump_task.cancel()

        # Wait for task termination (must add timeout)
        tasks_to_wait = [stdin_task, ws_task, scraper_task, cgm_task, pump_task]
        if ota_task:
            tasks_to_wait.append(ota_task)

        await asyncio.wait(
            tasks_to_wait,
            timeout=3.0,
            return_when=asyncio.ALL_COMPLETED,
        )
        print("Server closed, program exited.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Manual interruption, program terminated.")
