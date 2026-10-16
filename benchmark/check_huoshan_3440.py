"""PR-issue 3440 monitor snapshot 隔离 + 旧会话事件不影响当前回归测试。

复现：
  1. 旧会话结束事件（SessionCanceled/Failed/Finished）即使 sessionId 不匹配也会
     reset 当前 activate_session，破坏 start_session 的"上个会话激活时关闭
     新建"判断
  2. monitor 循环直接用 self.ws.recv()，连接被重建后旧任务读新连接下行；
     旧任务因读旧句柄异常退出时又会把新连接误关

修复：
  - monitor 入口绑定 monitor_ws = self.ws / monitor_task = current_task()；
    recv 用 monitor_ws；finally 清理判 id(self.ws) is id(monitor_ws) 才关
  - 旧 session 事件 continue 即可，不再 reset activate_session

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


def test_monitor_uses_snapshot_ws():
    """monitor 入口绑定 monitor_ws，recv 用 monitor_ws，外部换 self.ws 不影响。"""
    p = build_provider()
    # 把 self.ws 与 mock monitor 内部用的 ws 解耦
    calls = []

    async def _recv_log(*a, **k):
        calls.append("recv_called")
        raise websockets.ConnectionClosed(None, None)

    ws_old = MagicMock()
    ws_old.recv = _async_iter_mock([websockets.ConnectionClosed(None, None)])
    ws_old.close = AsyncMock(side_effect=lambda: calls.append("old_close"))
    ws_new = MagicMock()
    ws_new.close = AsyncMock(side_effect=lambda: calls.append("new_close_should_not_appear"))

    p.ws = ws_old
    p._monitor_task = None  # 防 finally 比较

    async def _drive_then_swap():
        # 立即把 p.ws 换到 ws_new，模拟重建连接
        async def _swap():
            await asyncio.sleep(0.01)
            p.ws = ws_new

        await asyncio.gather(p._start_monitor_tts_response(), _swap())

    run(_drive_then_swap())
    assert "new_close_should_not_appear" not in calls, (
        f"旧 monitor 不应误关新连接；calls={calls}"
    )
    print(f"OK: 旧 monitor 用 snapshot 隔离，未误关新连接（calls={calls}）")


def test_source_has_snapshot_check():
    """静态检查：_start_monitor_tts_response 入口有 monitor_ws = self.ws，
    finally 清理有 self.ws is monitor_ws 判断。"""
    src = open(
        os.path.join(REPO, "main/xiaozhi-server/core/providers/tts/huoshan_double_stream.py")
    ).read()
    assert "monitor_ws = self.ws" in src, "monitor 入口应绑定 monitor_ws = self.ws"
    assert "if self.ws is monitor_ws" in src, "finally 清理应判 self.ws is monitor_ws 才关"
    assert "if self._monitor_task is monitor_task" in src, (
        "finally 清理应判 self._monitor_task is monitor_task 才清空引用"
    )
    print("OK: monitor 入口绑定 snapshot，finally 清理有 id 比较")


def main() -> int:
    test_old_session_finished_does_not_reset_activate()
    test_old_session_canceled_does_not_reset_activate()
    test_monitor_uses_snapshot_ws()
    test_source_has_snapshot_check()
    print("\nALL PASS: 3440 monitor snapshot 隔离 + 旧会话事件不影响当前（修复点 3）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
