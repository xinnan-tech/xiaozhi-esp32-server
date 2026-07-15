"""
外部 Speaker 注入 — 真 WebSocket 端到端测试

起一个最小的真 WS server(websockets 库,真实 WS 连接 + 真实帧传输),接上
真的 TextMessageHandlerRegistry 和真的 SpeakerTextMessageHandler。模拟 lebot
客户端:WS 连接带 X-External-Speaker header,发 hello / listen / {type:speaker} /
opus 二进制 / listen stop,验证:

1. header 正确解析 → conn.external_vpr_enabled
2. 无 header → False(直连设备回归)
3. {type:speaker} 帧经 registry 路由到 SpeakerTextMessageHandler → conn.proxy_speaker 被设
4. 完整 lebot 式会话握手→听→识别→speaker→音频→停止

注:ConnectionHandler.handle_connection 全流程依赖 VAD/ASR/TTS/LLM/memory 全套 provider,
本环境起不了(libopus 缺 + provider 未配)。这里用的是与 connection.py 相同的 header 解析
逻辑(connection.py:210)和真的 registry / handler,测 WS 协议层 + 帧分发 + speaker 处理。

运行:python3 -m unittest tests.test_external_speaker_ws -v
"""
import asyncio
import json
import os
import sys
import unittest
from unittest.mock import MagicMock

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

# opuslib_next 需 libopus C 库,本环境没有;WS 层测试不需要真 opus 解码,mock 绕过
_opus = MagicMock()
_opus.OpusError = type("OpusError", (Exception,), {})
_opus.Decoder = MagicMock()
sys.modules.setdefault("opuslib_next", _opus)

import websockets
from core.handle.textMessageHandlerRegistry import TextMessageHandlerRegistry


class FakeConn:
    """模拟 ConnectionHandler 的 speaker 相关字段,避开重的 __init__(全套 provider)。"""

    def __init__(self):
        self.external_vpr_enabled = False
        self.proxy_speaker = None
        self.proxy_speaker_ready = asyncio.Event()
        self.headers = {}


class WSServer:
    """最小 WS server:复用 connection.py 的 header 解析逻辑 + 真 registry 分发文本帧。"""

    def __init__(self):
        self.registry = TextMessageHandlerRegistry()
        self.conns = []

    async def handler(self, ws):
        conn = FakeConn()
        conn.headers = dict(ws.request.headers)
        # 与 connection.py:210 完全相同的 header 解析
        conn.external_vpr_enabled = conn.headers.get("x-external-speaker") == "1"
        self.conns.append(conn)
        try:
            async for message in ws:
                if isinstance(message, (bytes, bytearray)):
                    continue  # 音频二进制帧,WS 层测试忽略
                try:
                    data = json.loads(message)
                except json.JSONDecodeError:
                    continue
                handler = self.registry.get_handler(data.get("type"))
                if handler:
                    try:
                        await handler.handle(conn, data)
                    except Exception:
                        # FakeConn 不提供完整 ConnectionHandler 接口;非 speaker 的
                        # handler(hello/listen 等)可能在此报错。本测试聚焦 speaker
                        # 路由,忽略其它 handler 的异常,保证后续帧继续处理。
                        pass
        except websockets.exceptions.ConnectionClosed:
            pass


class TestExternalSpeakerWebSocket(unittest.IsolatedAsyncioTestCase):
    """真 WS 端到端:模拟 lebot 客户端"""

    async def _run_session(self, send_header=True, frames=None):
        """起 server → 客户端发帧 → 返回 server 端的 conn"""
        server_app = WSServer()
        port = 18765
        server = await websockets.serve(server_app.handler, "127.0.0.1", port)
        try:
            headers = {"X-External-Speaker": "1"} if send_header else {}
            async with websockets.connect(
                f"ws://127.0.0.1:{port}", additional_headers=headers
            ) as ws:
                for frame in (frames or []):
                    if isinstance(frame, (bytes, bytearray)):
                        await ws.send(frame)
                    else:
                        await ws.send(json.dumps(frame))
                await asyncio.sleep(0.15)  # 让 server 处理完帧
        finally:
            server.close()
            await server.wait_closed()
        return server_app.conns[0] if server_app.conns else None

    async def test_header_marks_external_vpr(self):
        """X-External-Speaker: 1 → external_vpr_enabled = True"""
        conn = await self._run_session(frames=[
            {"type": "hello", "audio_params": {"format": "opus"}},
        ])
        self.assertIsNotNone(conn)
        self.assertTrue(conn.external_vpr_enabled)

    async def test_no_header_not_external(self):
        """无 header → external_vpr_enabled = False(直连设备回归)"""
        conn = await self._run_session(send_header=False, frames=[
            {"type": "hello", "audio_params": {"format": "opus"}},
        ])
        self.assertFalse(conn.external_vpr_enabled)

    async def test_speaker_frame_routed_and_stored(self):
        """{type:speaker} 帧经 registry 路由 → conn.proxy_speaker + event set"""
        speaker_frame = {"type": "speaker", "name": "张三", "relationship": "爸爸",
                         "person_id": "abc", "confidence": 0.92}
        conn = await self._run_session(frames=[
            {"type": "hello", "audio_params": {"format": "opus"}},
            {"type": "listen", "state": "start"},
            speaker_frame,
            b"\x00\x01\x02\x03",  # 模拟 opus 音频二进制帧
            {"type": "listen", "state": "stop"},
        ])
        self.assertEqual(conn.proxy_speaker, speaker_frame)
        self.assertTrue(conn.proxy_speaker_ready.is_set())

    async def test_full_lebot_like_session(self):
        """完整 lebot 会话:握手→听→识别→speaker→音频→停止"""
        conn = await self._run_session(frames=[
            {"type": "hello", "audio_params": {"format": "opus", "sample_rate": 16000}},
            {"type": "listen", "state": "start"},
            {"type": "speaker", "name": "李四", "relationship": "妈妈"},
            b"\x00" * 100,  # opus 帧
            b"\x01" * 100,
            {"type": "listen", "state": "stop"},
        ])
        self.assertTrue(conn.external_vpr_enabled)
        self.assertEqual(conn.proxy_speaker["name"], "李四")
        self.assertEqual(conn.proxy_speaker["relationship"], "妈妈")
        self.assertTrue(conn.proxy_speaker_ready.is_set())


if __name__ == "__main__":
    unittest.main(verbosity=2)
