"""PR-issue 3438 会话启动失败可感知回归测试。

复现：
  服务端拒绝 StartSession（SessionFailed）时，旧逻辑无任何处理分支：
  整轮无声、activate_session 卡 True，下一轮靠 close 兜底且无日志

修复（按评审收敛后的形态）：
  - start_session 发送即返回，不等确认帧（无 future 机制）
  - monitor matched 分支处理 SessionFailed：error 日志 + activate_session 复位

Usage:
    python benchmark/check_huoshan_3438.py
"""
from __future__ import annotations

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

from core.providers.tts.huoshan_double_stream import (  # noqa: E402
    EVENT_SessionFailed,
    EVENT_SessionStarted,
)

FULL_SERVER_RESPONSE = 0b1001
MsgTypeFlagWithEvent = 0b100


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


def test_start_session_fire_and_forget():
    """start_session 发送 StartSession 后立即返回，不等确认帧。"""
    p = build_provider()
    p.send_event = AsyncMock()
    p._ensure_connection = AsyncMock()
    run(p.start_session("test-session-id"))
    assert p.send_event.await_count == 1, "应恰好发送一次 StartSession"
    print("OK: start_session 发送即返回，不阻塞等确认")


def test_monitor_session_failed_resets_flag():
    """matched SessionFailed 帧：monitor 记 error 并复位 activate_session。"""
    p = build_provider()
    p.activate_session = True
    p.ws.recv = AsyncMock(
        side_effect=[
            _build_session_event_frame(EVENT_SessionFailed, p.conn.sentence_id),
            websockets.ConnectionClosed(None, None),
        ]
    )
    run(p._start_monitor_tts_response())
    assert p.activate_session is False, (
        f"SessionFailed 应复位 activate_session，实际 {p.activate_session}"
    )
    print("OK: SessionFailed 复位 activate_session，状态不卡 True")


def test_monitor_session_started_keeps_flag():
    """matched SessionStarted 帧：不触碰 activate_session（仍为 True）。"""
    p = build_provider()
    p.activate_session = True
    p.ws.recv = AsyncMock(
        side_effect=[
            _build_session_event_frame(EVENT_SessionStarted, p.conn.sentence_id),
            websockets.ConnectionClosed(None, None),
        ]
    )
    run(p._start_monitor_tts_response())
    assert p.activate_session is True, (
        f"SessionStarted 不应触碰 activate_session，实际 {p.activate_session}"
    )
    print("OK: SessionStarted 不影响 activate_session")


def main() -> int:
    test_start_session_fire_and_forget()
    test_monitor_session_failed_resets_flag()
    test_monitor_session_started_keeps_flag()
    print("\nALL PASS: 会话启动失败可感知（monitor 侧处理，无 future 机制）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
