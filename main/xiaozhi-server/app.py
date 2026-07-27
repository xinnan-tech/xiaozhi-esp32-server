import sys
import uuid
import signal
import asyncio
from aioconsole import ainput
from config.config_loader import load_config
from config.logger import setup_logging
from core.utils.util import get_local_ip, validate_mcp_endpoint
from core.http_server import SimpleHttpServer
from core.xiaozhi_server_facade import XiaozhiServerFacade
from core.utils.util import check_ffmpeg_installed
from core.utils.gc_manager import get_gc_manager
from config.manage_api_client import manage_api_http_close

TAG = __name__
logger = setup_logging()


async def wait_for_exit() -> None:
    """
    阻塞直到收到 Ctrl‑C / SIGTERM。
    - Unix: 使用 add_signal_handler
    - Windows: 依赖 KeyboardInterrupt
    """
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    if sys.platform != "win32":  # Unix / macOS
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop_event.set)
        await stop_event.wait()
    else:
        # Windows：await一个永远pending的fut，
        # 让 KeyboardInterrupt 冒泡到 asyncio.run，以此消除遗留普通线程导致进程退出阻塞的问题
        try:
            await asyncio.Future()
        except KeyboardInterrupt:  # Ctrl‑C
            pass


async def monitor_stdin():
    """监控标准输入，消费回车键"""
    while True:
        await ainput()  # 异步等待输入，消费回车


async def main():
    check_ffmpeg_installed()
    config = await load_config()

    # auth_key优先级：配置文件server.auth_key > manager-api.secret > 自动生成
    # auth_key用于jwt认证，比如视觉分析接口的jwt认证、ota接口的token生成与websocket认证
    # 获取配置文件中的auth_key
    auth_key = config["server"].get("auth_key", "")

    # 验证auth_key，无效则尝试使用manager-api.secret
    if not auth_key or len(auth_key) == 0 or "你" in auth_key:
        auth_key = config.get("manager-api", {}).get("secret", "")
        # 验证secret，无效则生成随机密钥
        if not auth_key or len(auth_key) == 0 or "你" in auth_key:
            auth_key = str(uuid.uuid4().hex)

    config["server"]["auth_key"] = auth_key

    # 添加 stdin 监控任务
    stdin_task = asyncio.create_task(monitor_stdin())

    # 启动全局GC管理器（5分钟清理一次）
    gc_manager = get_gc_manager(interval_seconds=300)
    await gc_manager.start()

    # 启动小智服务器门面
    xiaozhi_server = XiaozhiServerFacade(config)
    ota_server = None
    ota_task = None
    try:
        # Facade.start() returns after every listener is ready. Await it so bind
        # or configuration failures stop startup instead of leaving a partial process.
        await xiaozhi_server.start()
        ota_server = SimpleHttpServer(config)
        ota_task = asyncio.create_task(
            ota_server.start(), name="xiaozhi-http-server"
        )
        await ota_server.wait_started(
            ota_task,
            timeout=float(config.get("server_startup_timeout", 10)),
        )
    except Exception:
        if ota_server:
            try:
                await ota_server.stop()
            except Exception as cleanup_error:
                logger.bind(tag=TAG).error(f"停止HTTP服务器失败: {cleanup_error}")
        if ota_task:
            if not ota_task.done():
                ota_task.cancel()
            await asyncio.gather(ota_task, return_exceptions=True)
        try:
            await xiaozhi_server.stop()
        except Exception as cleanup_error:
            logger.bind(tag=TAG).error(f"停止协议服务器失败: {cleanup_error}")
        try:
            await gc_manager.stop()
        except Exception as cleanup_error:
            logger.bind(tag=TAG).error(f"停止GC管理器失败: {cleanup_error}")
        try:
            await manage_api_http_close()
        except Exception as cleanup_error:
            logger.bind(tag=TAG).error(f"关闭管理API客户端失败: {cleanup_error}")
        stdin_task.cancel()
        await asyncio.gather(stdin_task, return_exceptions=True)
        raise

    read_config_from_api = config.get("read_config_from_api", False)
    port = int(config["server"].get("http_port", 8003))
    if not read_config_from_api:
        logger.bind(tag=TAG).info(
            "OTA接口是\t\thttp://{}:{}/xiaozhi/ota/",
            get_local_ip(),
            port,
        )
    logger.bind(tag=TAG).info(
        "视觉分析接口是\thttp://{}:{}/mcp/vision/explain",
        get_local_ip(),
        port,
    )
    mcp_endpoint = config.get("mcp_endpoint", None)
    if mcp_endpoint is not None and "你" not in mcp_endpoint:
        # 校验MCP接入点格式
        if validate_mcp_endpoint(mcp_endpoint):
            logger.bind(tag=TAG).info("mcp接入点是\t{}", mcp_endpoint)
            # 将mcp计入点地址转成调用点
            mcp_endpoint = mcp_endpoint.replace("/mcp/", "/call/")
            config["mcp_endpoint"] = mcp_endpoint
        else:
            logger.bind(tag=TAG).error("mcp接入点不符合规范")
            config["mcp_endpoint"] = "你的接入点 websocket地址"

    # 显示协议连接信息
    connection_info = xiaozhi_server.get_connection_info()

    # WebSocket信息
    websocket_info = connection_info.get("websocket", {})
    if websocket_info.get("enabled", False):
        websocket_port = websocket_info.get("port", 8000)
        logger.bind(tag=TAG).info(
            "WebSocket地址是\tws://{}:{}/xiaozhi/v1/",
            get_local_ip(),
            websocket_port,
        )

    # 显示启用的协议
    enabled_protocols = xiaozhi_server.config.get("enabled_protocols", [])
    logger.bind(tag=TAG).info(f"启用的协议: {', '.join(enabled_protocols)}")

    if "websocket" in enabled_protocols:
        logger.bind(tag=TAG).info(
            "=======上面的WebSocket地址请勿用浏览器访问======="
        )
        logger.bind(tag=TAG).info(
            "如想测试WebSocket请启动digital-human模块，打开浏览器交互测试"
        )

    logger.bind(tag=TAG).info(
        "=============================================================\n"
    )

    try:
        await wait_for_exit()  # 阻塞直到收到退出信号
    except asyncio.CancelledError:
        print("任务被取消，清理资源中...")
    finally:
        shutdown_errors = []
        if ota_server:
            try:
                await ota_server.stop()
            except Exception as e:
                shutdown_errors.append(("HTTP服务器", e))
                logger.bind(tag=TAG).error(f"停止HTTP服务器失败: {e}")

        # 停止小智服务器
        try:
            await xiaozhi_server.stop()
        except Exception as e:
            shutdown_errors.append(("协议服务器", e))
            logger.bind(tag=TAG).error(f"停止小智服务器失败: {e}")

        # 停止全局GC管理器
        try:
            await gc_manager.stop()
        except Exception as e:
            shutdown_errors.append(("GC管理器", e))
            logger.bind(tag=TAG).error(f"停止GC管理器失败: {e}")

        try:
            await manage_api_http_close()
        except Exception as e:
            shutdown_errors.append(("管理API客户端", e))
            logger.bind(tag=TAG).error(f"关闭管理API客户端失败: {e}")

        # stdin 可立即取消；HTTP task 先获得窗口完成 runner.cleanup()。
        stdin_task.cancel()
        await asyncio.gather(stdin_task, return_exceptions=True)

        if ota_task:
            done, pending = await asyncio.wait({ota_task}, timeout=3.0)
            if pending:
                ota_task.cancel()
                await asyncio.gather(ota_task, return_exceptions=True)
            elif done and not ota_task.cancelled():
                try:
                    ota_task.result()
                except Exception as e:
                    shutdown_errors.append((ota_task.get_name(), e))
                    logger.bind(tag=TAG).error(
                        f"后台任务退出失败: {ota_task.get_name()}: {e}"
                    )

        # If task cancellation or its first cleanup attempt retained the
        # runner, retry after the task has fully relinquished ownership.
        if ota_server:
            try:
                await ota_server.stop()
            except Exception as e:
                shutdown_errors.append(("HTTP服务器重试清理", e))
                logger.bind(tag=TAG).error(f"重试停止HTTP服务器失败: {e}")
        print("服务器已关闭，程序退出。")
        if shutdown_errors:
            details = ", ".join(
                f"{owner}: {error}" for owner, error in shutdown_errors
            )
            raise RuntimeError(f"服务器清理失败: {details}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("手动中断，程序终止。")
