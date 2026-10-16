"""PR-issue 3441 parser_response 四处二进制协议解析错误回归测试。

复现：
  1. serialization_method 恒为 0：旧 num=0b00001111 被错用为移位数，>> 15 恒 0
  2. message_type 判断恒真：旧 `== FULL_SERVER_RESPONSE or AUDIO_ONLY_RESPONSE` 优先级下
     AUDIO_ONLY_RESPONSE=0b1011 作为真值使条件恒真
  3. offset 硬编码 4：旧 `res[offset:8]` 与 `header_size * 4` 在 header_size=1 时重合但
     header_size=2 时全错位
  4. SessionCanceled 走 else 分支被当作 sessionId+payload 解析：协议层实际为
     sessionId+meta_json

Usage:
    python benchmark/check_huoshan_parser_3441.py
"""
from __future__ import annotations

import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER = os.path.join(REPO, "main", "xiaozhi-server")
if SERVER not in sys.path:
    sys.path.insert(0, SERVER)

from core.providers.tts.huoshan_double_stream import (  # noqa: E402
    TTSProvider,
    FULL_SERVER_RESPONSE,
    AUDIO_ONLY_RESPONSE,
    ERROR_INFORMATION,
    EVENT_SessionStarted,
    EVENT_SessionFailed,
    EVENT_SessionFinished,
    EVENT_SessionCanceled,
    EVENT_ConnectionStarted,
    MsgTypeFlagWithEvent,
)


def make_header_byte0(protocol_version=0b0001, header_size=1) -> int:
    return (protocol_version << 4) | header_size


def make_header_byte1(message_type, flags) -> int:
    return (message_type << 4) | flags


def make_header_byte2(serialization_method, compression_type) -> int:
    return (serialization_method << 4) | compression_type


def make_str_field(s: str) -> bytes:
    enc = s.encode("utf-8")
    return len(enc).to_bytes(4, "big", signed=True) + enc


def build_frame(
    message_type: int,
    event: int | None,
    session_id: str | None,
    meta_json: str | None = None,
    payload: bytes | None = None,
    header_size: int = 1,
    serialization_method: int = 0b0001,
    flags: int = MsgTypeFlagWithEvent,
) -> bytes:
    res = bytearray()
    res.append(make_header_byte0(header_size=header_size))
    res.append(make_header_byte1(message_type, flags))
    res.append(make_header_byte2(serialization_method, 0b0000))
    res.append(0)
    if header_size > 1:
        res.extend(b"\x00" * (header_size - 1) * 4)
    if event is not None:
        res.extend(event.to_bytes(4, "big", signed=True))
    if session_id is not None:
        res.extend(make_str_field(session_id))
    if meta_json is not None:
        res.extend(make_str_field(meta_json))
    if payload is not None:
        res.extend(len(payload).to_bytes(4, "big", signed=True))
        res.extend(payload)
    return bytes(res)


def fresh_provider() -> TTSProvider:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "_huoshan_mock",
        os.path.join(os.path.dirname(__file__), "_huoshan_mock.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.build_provider()


def test_serialization_method_extracted_correctly():
    p = fresh_provider()
    frame = build_frame(
        message_type=FULL_SERVER_RESPONSE,
        event=EVENT_SessionStarted,
        session_id="sid",
        meta_json='{"k":"v"}',
        serialization_method=0b0010,
    )
    res = p.parser_response(frame)
    assert res.header.serialization_method == 0b0010, (
        f"serialization_method 应为 0b0010=2，实际 {res.header.serialization_method:#06b}"
    )
    assert res.optional.event == EVENT_SessionStarted
    assert res.optional.sessionId == "sid"
    assert res.optional.response_meta_json == '{"k":"v"}'
    print("OK: serialization_method 正确从 res[2]>>4 提取（修复点 1）")


def test_message_type_branch_includes_audio_only():
    """修复前 `== FULL or AUDIO_ONLY_RESPONSE` 优先级下恒真。
    现版必须用 in (...) 限定，否则别的不支持的 message_type 也进同一分支。"""
    p = fresh_provider()
    # message_type = 0b0001 (FULL_CLIENT_REQUEST) 不应进 FULL/AUDIO 分支，
    # 应进 ERROR_INFORMATION 之外的默认（不解析 event）
    frame = build_frame(
        message_type=0b0001,
        event=EVENT_SessionStarted,
        session_id="sid",
    )
    res = p.parser_response(frame)
    assert res.optional.event == 0, (
        f"message_type=FULL_CLIENT_REQUEST 不应解析 event，实际 event={res.optional.event}"
    )
    # AUDIO_ONLY_RESPONSE 仍能进 FULL/AUDIO 分支解析
    frame2 = build_frame(
        message_type=AUDIO_ONLY_RESPONSE,
        event=EVENT_SessionFinished,
        session_id="sid2",
        meta_json='{"e":"ok"}',
    )
    res2 = p.parser_response(frame2)
    assert res2.optional.event == EVENT_SessionFinished
    assert res2.optional.sessionId == "sid2"
    print("OK: message_type in (FULL_SERVER_RESPONSE, AUDIO_ONLY_RESPONSE) 正确分支（修复点 2）")


def test_offset_respects_header_size():
    """header_size=2 时 optional 起始偏移应为 8，不是 4。"""
    p = fresh_provider()
    frame = build_frame(
        message_type=FULL_SERVER_RESPONSE,
        event=EVENT_SessionStarted,
        session_id="s",
        meta_json="m",
        header_size=2,
    )
    res = p.parser_response(frame)
    assert res.optional.event == EVENT_SessionStarted
    assert res.optional.sessionId == "s"
    assert res.optional.response_meta_json == "m"
    print("OK: offset = header.header_size * 4 支持扩展头（修复点 3）")


def test_session_canceled_parses_sessionid_and_meta():
    """修复前 SessionCanceled 落 else 分支被误读为 sessionId+payload。"""
    p = fresh_provider()
    meta = '{"reason":"user cancel"}'
    frame = build_frame(
        message_type=FULL_SERVER_RESPONSE,
        event=EVENT_SessionCanceled,
        session_id="cancel-sid",
        meta_json=meta,
    )
    res = p.parser_response(frame)
    assert res.optional.event == EVENT_SessionCanceled
    assert res.optional.sessionId == "cancel-sid"
    assert res.optional.response_meta_json == meta
    print("OK: EVENT_SessionCanceled 按协议解析 sessionId+meta（修复点 4）")


def main() -> int:
    test_serialization_method_extracted_correctly()
    test_message_type_branch_includes_audio_only()
    test_offset_respects_header_size()
    test_session_canceled_parses_sessionid_and_meta()
    print("\nALL PASS: parser_response 4 处协议解析错误全修")
    return 0


if __name__ == "__main__":
    sys.exit(main())
