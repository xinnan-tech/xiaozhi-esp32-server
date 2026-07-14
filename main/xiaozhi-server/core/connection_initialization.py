import asyncio


DEFAULT_BIND_STATUS_TIMEOUT_SECONDS = 10.0
MIN_BIND_STATUS_TIMEOUT_SECONDS = 1.0
MAX_BIND_STATUS_TIMEOUT_SECONDS = 60.0


def bind_status_timeout_seconds(config) -> float:
    """返回等待设备绑定状态的有界超时时间。"""
    try:
        raw = config.get("server", {}).get(
            "bind_status_timeout_seconds", DEFAULT_BIND_STATUS_TIMEOUT_SECONDS
        )
        timeout = float(raw)
    except (AttributeError, TypeError, ValueError):
        timeout = DEFAULT_BIND_STATUS_TIMEOUT_SECONDS
    return min(
        max(timeout, MIN_BIND_STATUS_TIMEOUT_SECONDS),
        MAX_BIND_STATUS_TIMEOUT_SECONDS,
    )


async def wait_for_bind_status(event: asyncio.Event, config) -> bool:
    """等待绑定状态就绪，超时时返回 False。"""
    try:
        await asyncio.wait_for(
            event.wait(), timeout=bind_status_timeout_seconds(config)
        )
    except asyncio.TimeoutError:
        return False
    return True
