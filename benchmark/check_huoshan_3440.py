"""PR-issue 3440 旧会话事件不影响当前会话 + 取消屏障回归测试。

复现：
  旧会话结束事件（SessionCanceled/Failed/Finished）即使 sessionId 不匹配也会
  reset 当前 activate_session，破坏 start_session 的"上个会话激活时关闭
  新建"判断

修复（按评审收敛后的形态）：
  - 旧 session 事件 continue 跳过，不再 reset activate_session
  - 旧连接误关/偷读由建连前的取消屏障（_cancel_monitor_task 等待任务退出）
    保证，不依赖 snapshot 判 id

Usage:
    python benchmark/check_huoshan_3440.py
"""
from __future__ import annotations

import asyncio
import importlib.util
import os
import sys
from unittest.mock import AsyncMock, MagicMock

import websockets

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_mock():
    spec = importlib.util.spec_from_file_location(
        "_huoshan_mock", os.path.join(os.path.dirname(__file__), "_huoshan_mock.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_mock = _load_mock()
build_provider = _mock.build_provider
run = _mock.run

FULL_SERVER_RESPONSE = 0b1001
MsgTypeFlagWithEvent = 0b100
EVENT_SessionFinished = 152
EVENT_SessionCanceled = 151


def _build_session_event_frame(event: int, session_id: str, meta: str = "{}") -> bytes:
    res = bytearray()
    res.append((0b0001 << 4) | 1)
    res.append((FULL_SERVER_RESPONSE << 4) | MsgTypeFlagWithEvent)
    res.append((0b0001 << 4) | 0)
    res.append(0)
    res.extend(event.to_bytes(4, "big", signed=True))
    enc = session_id.encode("utf-8")
    res.extend(len(enc).to_bytes(4, "big", signed=True))
    res.extend(enc)
    meta_bytes = meta.encode("utf-8")
    res.extend(len(meta_bytes).to_bytes(4, "big", signed=True))
    res.extend(meta_bytes)
    return bytes(res)


def _async_iter_mock(items):
    m = AsyncMock()
    it = iter(items)

    async def _next(*a, **k):
        try:
            v = next(it)
        except StopIteration:
            raise websockets.ConnectionClosed(None, None)
        if isinstance(v, Exception):
            raise v
        return v

    m.side_effect = _next
    return m


def test_old_session_finished_does_not_reset_activate():
    """旧 session 的 SessionFinished 不应 reset 当前 activate_session。"""
    p = build_provider()
    p.activate_session = True
    p.ws.recv = _async_iter_mock(
        [_build_session_event_frame(EVENT_SessionFinished, "OLD-sid-not-mine")]
    )
    run(p._start_monitor_tts_response())
    assert p.activate_session is True, (
        f"旧 session 结束事件不应 reset 当前 activate_session，实际 {p.activate_session}"
    )
    print("OK: 旧 session SessionFinished 不 reset 当前 activate_session")


def test_old_session_canceled_does_not_reset_activate():
    p = build_provider()
    p.activate_session = True
    p.ws.recv = _async_iter_mock(
        [_build_session_event_frame(EVENT_SessionCanceled, "OLD-sid-not-mine")]
    )
    run(p._start_monitor_tts_response())
    assert p.activate_session is True
    print("OK: 旧 session SessionCanceled 不 reset 当前 activate_session")


def test_cancel_barrier_awaits_monitor_exit():
    """取消屏障原语：_cancel_monitor_task 返回时旧监听任务必须已完全退出。

    这是"旧监听任务不会读新连接/误关新连接"的根本保证：建新连接前
    旧任务已被 cancel + await 收尸，其后才允许重赋 self.ws。
    """
    p = build_provider()

    async def _block_recv(*a, **k):
        await asyncio.Event().wait()  # 模拟阻塞在 recv

    p.ws = MagicMock()
    p.ws.recv = AsyncMock(side_effect=_block_recv)
    p.ws.close = AsyncMock()

    async def _drive():
        m = asyncio.create_task(p._start_monitor_tts_response())
        p._monitor_task = m
        await asyncio.sleep(0.01)
        assert not m.done(), "监听任务应仍在运行"
        await p._cancel_monitor_task()
        assert m.done() and m.cancelled(), (
            "_cancel_monitor_task 返回时旧监听任务必须已退出"
        )
        assert p._monitor_task is None, "屏障应清空 _monitor_task 引用"

    run(_drive())
    print("OK: 取消屏障等待旧监听任务完全退出后才返回")


def test_source_has_cancel_barrier_and_skip():
    """静态检查：mismatch 纯跳过存在；monitor finally 不再复位 activate_session。"""
    src = open(
        os.path.join(REPO, "main/xiaozhi-server/core/providers/tts/huoshan_double_stream.py"),
        encoding="utf-8",
    ).read()
    assert "self.conn.sentence_id != res.optional.sessionId" in src, (
        "mismatch 分支应纯跳过（continue），不复位 activate_session"
    )
    monitor_src = src.split("async def _start_monitor_tts_response")[1]
    finally_src = monitor_src.split("finally:")[1]
    assert "activate_session" not in finally_src, (
        "monitor finally 不应触碰 activate_session（避免覆盖新会话状态）"
    )
    print("OK: mismatch 纯跳过存在，finally 不触碰 activate_session")


def main() -> int:
    test_old_session_finished_does_not_reset_activate()
    test_old_session_canceled_does_not_reset_activate()
    test_cancel_barrier_awaits_monitor_exit()
    test_source_has_cancel_barrier_and_skip()
    print("\nALL PASS: 3440 旧会话事件不影响当前 + 取消屏障保证")
    return 0


if __name__ == "__main__":
    sys.exit(main())
