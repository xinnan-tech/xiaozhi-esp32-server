"""S2S provider 的创建与挂接（与 core/utils/llm.py 的 create_instance 同一套路）。"""
import asyncio
import importlib
import os
import sys

from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


def create_instance(class_name, *args, **kwargs):
    """按 type 名加载 core/providers/s2s/<type>/<type>.py 里的 S2SProvider。"""
    if os.path.exists(os.path.join("core", "providers", "s2s", class_name, f"{class_name}.py")):
        lib_name = f"core.providers.s2s.{class_name}.{class_name}"
        if lib_name not in sys.modules:
            sys.modules[lib_name] = importlib.import_module(f"{lib_name}")
        return sys.modules[lib_name].S2SProvider(*args, **kwargs)

    raise ValueError(f"不支持的S2S类型: {class_name}，请检查该配置的type是否设置正确")


def s2s_selected(conn) -> bool:
    """这条连接是否选了 S2S（provider 可能还没建成）。"""
    return bool((conn.config.get("selected_module") or {}).get("S2S"))


async def s2s_on_text(conn, text: str) -> None:
    """文字入口：provider 建成了就直接给它；还没建成（唤醒词 detect 常比它早到一秒）就先记着，建成后回放。"""
    if conn.s2s is not None:
        await conn.s2s.on_text(text)
        return
    pending = getattr(conn, "_s2s_pending_texts", None)
    if pending is None:
        pending = conn._s2s_pending_texts = []
    pending.append(text)


async def drain_pending_texts(conn) -> None:
    pending = getattr(conn, "_s2s_pending_texts", None)
    if not pending or conn.s2s is None:
        return
    texts, pending[:] = list(pending), []
    for t in texts:
        await conn.s2s.on_text(t)


def attach_s2s(conn):
    """在 ConnectionHandler._initialize_components（执行器线程）里调用。

    selected_module.S2S 没填 → None（原版级联）。填了就创建 provider 并在连接的事件循环上打开上游会话，
    整段限时 connect_timeout_s + 1 秒；任何失败都返回 None 并记一条警告，连接照常走级联，设备无感。
    """
    selected = (conn.config.get("selected_module") or {}).get("S2S")
    if not selected:
        return None
    cfg = (conn.config.get("S2S") or {}).get(selected)
    if not isinstance(cfg, dict):
        conn.logger.bind(tag=TAG).warning(f"selected_module.S2S={selected} 但没有对应的 S2S 配置块，回退级联")
        return None
    s2s_type = cfg.get("type", selected)
    timeout = float(cfg.get("connect_timeout_s", 4)) + 1.0
    provider = None
    fut = None
    try:
        provider = create_instance(s2s_type, cfg, conn)
        fut = asyncio.run_coroutine_threadsafe(provider.open(), conn.loop)
        fut.result(timeout=timeout)
    except Exception as e:  # noqa: BLE001
        conn.logger.bind(tag=TAG).warning(f"S2S {selected} 打开失败，回退原版级联: {type(e).__name__}: {e}")
        if fut is not None:
            fut.cancel()  # 超时的那次 open() 可能还在跑：取消掉，别让它事后建成一个没人管的会话
        if provider is not None:
            try:
                asyncio.run_coroutine_threadsafe(provider.close(), conn.loop)
            except Exception:  # noqa: BLE001
                pass
        return None
    conn.logger.bind(tag=TAG).info(f"S2S {selected} 已接管本连接（不建 TTS / ASR）")
    # 兜底：组件初始化后面某步失败、after_components_ready 没被调到时，建成前排队的文字也要送出去
    # 这里在执行器线程：loop.call_later 不是线程安全的，要经 call_soon_threadsafe 排进事件循环再定时
    conn.loop.call_soon_threadsafe(conn.loop.call_later, 3.0, lambda: asyncio.ensure_future(drain_pending_texts(conn)))
    return provider
