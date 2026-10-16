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

TAG = __name__

logger = setup_logging()


async def wait_for_exit() -> None:
    """
    Wait until Ctrl+C or SIGTERM is received.
    - Unix: uses add_signal_handler.
    - Windows: relies on KeyboardInterrupt.
    """
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    if sys.platform != "win32":  # Unix / macOS
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop_event.set)

        await stop_event.wait()
    else:
        # Windows: wait indefinitely to allow KeyboardInterrupt
        # to propagate to asyncio.run, preventing remaining
        # threads from blocking the shutdown process.
        try:
            await asyncio.Future()
        except KeyboardInterrupt:  # Ctrl+C
            pass


async def monitor_stdin():
    """Monitor standard input and wait for Enter to be pressed."""
    while True:
        await ainput()  # Wait for input asynchronously


async def main():
    check_ffmpeg_installed()
    config = await load_config()

    # Authentication key priority:
    # server.auth_key > manager-api.secret > automatically generated key.
    # The key is used for JWT authentication, visual analysis,
    # OTA token generation, and WebSocket authentication.

    # Retrieve the authentication key from the configuration file.
    auth_key = config["server"].get("auth_key", "")

    # If the key is invalid, try using the management API secret.
    if not auth_key or len(auth_key) == 0 or "你" in auth_key:
        auth_key = config.get("manager-api", {}).get("secret", "")

        # If the secret is also invalid, generate a random key.
        if not auth_key or len(auth_key) == 0 or "你" in auth_key:
            auth_key = str(uuid.uuid4().hex)

    config["server"]["auth_key"] = auth_key

    # Start the standard input monitoring task.
    stdin_task = asyncio.create_task(monitor_stdin())

    # Start the global garbage collection manager (cleanup every 5 minutes).
    gc_manager = get_gc_manager(interval_seconds=300)
    await gc_manager.start()

    # Start the WebSocket server.
    ws_server = WebSocketServer(config)
    ws_task = asyncio.create_task(ws_server.start())

    # Start the simple HTTP server.
    ota_server = SimpleHttpServer(config)
    ota_task = asyncio.create_task(ota_server.start())

    read_config_from_api = config.get("read_config_from_api", False)
    port = int(config["server"].get("http_port", 8003))

    if not read_config_from_api:
        logger.bind(tag=TAG).info(
            "OTA interface available at:\thttp://{}:{}/xiaozhi/ota/",
            get_local_ip(),
            port,
        )

    logger.bind(tag=TAG).info(
        "Visual analysis interface available at:\thttp://{}:{}/mcp/vision/explain",
        get_local_ip(),
        port,
    )

    mcp_endpoint = config.get("mcp_endpoint", None)

    if mcp_endpoint is not None and "你" not in mcp_endpoint:
        # Validate the MCP endpoint URL format.
        if validate_mcp_endpoint(mcp_endpoint):
            logger.bind(tag=TAG).info(
                "MCP endpoint: {}",
                mcp_endpoint,
            )

            # Convert the MCP endpoint URL to the corresponding call URL.
            mcp_endpoint = mcp_endpoint.replace("/mcp/", "/call/")
            config["mcp_endpoint"] = mcp_endpoint
        else:
            logger.bind(tag=TAG).error(
                "The MCP endpoint URL has an invalid format."
            )
            config["mcp_endpoint"] = "MCP endpoint WebSocket URL"

    # Retrieve the WebSocket configuration, using safe default values.
    websocket_port = 8000
    server_config = config.get("server", {})

    if isinstance(server_config, dict):
        websocket_port = int(server_config.get("port", 8000))

    logger.bind(tag=TAG).info(
        "WebSocket endpoint available at:\tws://{}:{}/xiaozhi/v1/",
        get_local_ip(),
        websocket_port,
    )

    logger.bind(tag=TAG).info(
        "======= The endpoint above uses the WebSocket protocol. Do not access it through a browser. ======="
    )

    logger.bind(tag=TAG).info(
        "To test the WebSocket connection, start the digital-human module and open the interaction test in your browser."
    )

    logger.bind(tag=TAG).info(
        "================================================================================\n"
    )

    try:
        await wait_for_exit()  # Wait for a shutdown signal.
    except asyncio.CancelledError:
        print("Task cancelled. Cleaning up resources...")

    finally:
        # Stop the global garbage collection manager.
        await gc_manager.stop()

        # Cancel all tasks to ensure a clean shutdown.
        stdin_task.cancel()
        ws_task.cancel()

        if ota_task:
            ota_task.cancel()

        # Wait for the tasks to finish, with a timeout.
        await asyncio.wait(
            [stdin_task, ws_task, ota_task]
            if ota_task
            else [stdin_task, ws_task],
            timeout=3.0,
            return_when=asyncio.ALL_COMPLETED,
        )

        print("Server stopped. Exiting the program.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Manual interruption detected. Shutting down the program.")
