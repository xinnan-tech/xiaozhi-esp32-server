import sys
import uuid
import signal
import asyncio
import json
import os
try:
    import redis.asyncio as aioredis  # prefer redis>=5
except Exception:
    import aioredis  # fallback for legacy envs
from aioconsole import ainput
from config.settings import load_config
from config.logger import setup_logging
from core.utils.util import get_local_ip, validate_mcp_endpoint
from core.http_server import SimpleHttpServer
from core.websocket_server import WebSocketServer
from core.utils.util import check_ffmpeg_installed

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
    config = load_config()
    # 打印当前工作目录，便于定位保存文件的真实位置
    logger.bind(tag=TAG).info("当前工作目录: {}", os.getcwd())

    # 默认使用manager-api的secret作为auth_key
    # 如果secret为空，则生成随机密钥
    # auth_key用于jwt认证，比如视觉分析接口的jwt认证
    auth_key = config.get("manager-api", {}).get("secret", "")
    if not auth_key or len(auth_key) == 0 or "你" in auth_key:
        auth_key = str(uuid.uuid4().hex)
    config["server"]["auth_key"] = auth_key

    # 添加 stdin 监控任务
    stdin_task = asyncio.create_task(monitor_stdin())
    # 初始化 Redis（供摄像头帧转发与指令分发）
    redis_cfg = config.get("redis", {}) or {}
    redis_url = config.get("redis", {}).get("url")
    if not redis_url:
        host = redis_cfg.get("host", "192.168.1.13")
        port = int(redis_cfg.get("port", 6379))
        db = int(redis_cfg.get("database", 0))
        password = redis_cfg.get("password", "redis_DbiKM4")
        if password:
            redis_url = f"redis://:{password}@{host}:{port}/{db}"
        else:
            redis_url = f"redis://{host}:{port}/{db}"
    try:
        redis = await aioredis.from_url(redis_url, encoding="utf-8", decode_responses=True)
        logger.bind(tag=TAG).info("Redis 已连接: {}", redis_url)
    except Exception as e:
        redis = None
        logger.bind(tag=TAG).error("Redis 连接失败，将不启用视频转发功能: {}", str(e))

    # 启动 Simple http 服务器
    ota_server = SimpleHttpServer(config)
    # 让 HTTP 服务器能够访问 Redis
    if redis:
        ota_server.camera_handler.set_redis(redis)
    
    # 启动 WebSocket 服务器（注入 redis 和 camera_handler）
    ws_server = WebSocketServer(config, redis=redis, camera_handler=ota_server.camera_handler)
    ws_task = asyncio.create_task(ws_server.start())
    ota_task = asyncio.create_task(ota_server.start())

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
    logger.bind(tag=TAG).info(
        "摄像头控制接口是\thttp://{}:{}/camera/{{device_id}}/start",
        get_local_ip(),
        port,
    )
    logger.bind(tag=TAG).info(
        "摄像头流媒体接口是\thttp://{}:{}/camera/{{device_id}}/stream",
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

    # 获取WebSocket配置，使用安全的默认值
    websocket_port = 8000
    server_config = config.get("server", {})
    if isinstance(server_config, dict):
        websocket_port = int(server_config.get("port", 8000))

    logger.bind(tag=TAG).info(
        "Websocket地址是\tws://{}:{}/xiaozhi/v1/",
        get_local_ip(),
        websocket_port,
    )

    logger.bind(tag=TAG).info(
        "=======上面的地址是websocket协议地址，请勿用浏览器访问======="
    )
    logger.bind(tag=TAG).info(
        "如想测试websocket请用谷歌浏览器打开test目录下的test_page.html"
    )
    logger.bind(tag=TAG).info(
        "=============================================================\n"
    )

    try:
        await wait_for_exit()  # 阻塞直到收到退出信号
    except asyncio.CancelledError:
        print("任务被取消，清理资源中...")
    finally:
        # 取消所有任务（关键修复点）
        stdin_task.cancel()
        ws_task.cancel()
        if ota_task:
            ota_task.cancel()

        # 等待任务终止（必须加超时）
        await asyncio.wait(
            [stdin_task, ws_task, ota_task] if ota_task else [stdin_task, ws_task],
            timeout=3.0,
            return_when=asyncio.ALL_COMPLETED,
        )
        print("服务器已关闭，程序退出。")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("手动中断，程序终止。")
