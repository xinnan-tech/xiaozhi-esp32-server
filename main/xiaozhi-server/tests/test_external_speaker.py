"""
外部 Speaker 注入(lebot 代理)— 单元 + 集成测试

覆盖:
1. resolve_speaker_name:纯函数,speaker 帧 → speaker_name 拼接
2. SpeakerTextMessageHandler:收帧 → 写 proxy_speaker + set event
3. handle_voice_stop 的 external_vpr_enabled 分支(集成,测实际改动逻辑):
   - 有 name+relationship → enhanced_text 含 "name(relationship)"
   - 仅 name → "name"
   - 超时(无 proxy_speaker)→ "未知说话人"
   - 非 external → 走现有 VoiceprintProvider(回归)

注:opuslib_next 需 libopus 系统库,测试环境用 mock 绕过(handle_voice_stop 走 pcm 不解码)。
真 WS 端到端(起 server + 模拟 lebot WS 客户端)需完整 provider 配置,见 spec §8,留给部署环境。

运行:python3 -m unittest tests.test_external_speaker -v
"""
import asyncio
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

# opuslib_next 需 libopus 系统库,测试环境用 mock 绕过(handle_voice_stop 走 pcm 不解码)
_opus = MagicMock()
_opus.OpusError = type("OpusError", (Exception,), {})
_opus.Decoder = MagicMock()
sys.modules.setdefault("opuslib_next", _opus)

from core.handle.textHandler.speakerMessageHandler import (
    SpeakerTextMessageHandler,
    resolve_speaker_name,
)
from core.providers.asr.base import ASRProviderBase
from core.utils.dialogue import Dialogue, Message


def _mock_conn(external=True, proxy_speaker=None, voiceprint_provider=None):
    """构造测试用 conn。proxy_speaker 非 None 时认为 speaker 帧已到达(event set)。"""
    conn = MagicMock()
    conn.external_vpr_enabled = external
    conn.proxy_speaker = proxy_speaker
    conn.proxy_speaker_ready = asyncio.Event()
    if proxy_speaker is not None:
        conn.proxy_speaker_ready.set()
    conn.session_id = "session-1"
    conn.audio_format = "pcm"  # 跳过 decode_opus
    conn.voiceprint_provider = voiceprint_provider
    conn.current_speaker = None
    return conn


class TestResolveSpeakerName(unittest.TestCase):
    """resolve_speaker_name:外部 speaker 帧 → speaker_name"""

    def test_name_with_relationship(self):
        self.assertEqual(
            resolve_speaker_name({"name": "张三", "relationship": "爸爸"}),
            "张三(爸爸)",
        )

    def test_name_only(self):
        self.assertEqual(resolve_speaker_name({"name": "李四"}), "李四")

    def test_no_name_returns_unknown(self):
        self.assertEqual(resolve_speaker_name({"relationship": "爸爸"}), "未知说话人")

    def test_none_returns_unknown(self):
        self.assertEqual(resolve_speaker_name(None), "未知说话人")

    def test_empty_name_returns_unknown(self):
        self.assertEqual(resolve_speaker_name({"name": ""}), "未知说话人")

    def test_extra_fields_ignored(self):
        self.assertEqual(
            resolve_speaker_name(
                {"person_id": "abc", "name": "王五", "relationship": "儿子",
                 "confidence": 0.9}
            ),
            "王五(儿子)",
        )


class TestSpeakerHandler(unittest.TestCase):
    """SpeakerTextMessageHandler"""

    def test_handle_stores_frame_and_sets_event(self):
        conn = MagicMock()
        conn.proxy_speaker_ready = asyncio.Event()
        self.assertFalse(conn.proxy_speaker_ready.is_set())

        handler = SpeakerTextMessageHandler()
        frame = {"type": "speaker", "name": "张三", "relationship": "爸爸"}
        asyncio.run(handler.handle(conn, frame))

        self.assertEqual(conn.proxy_speaker, frame)
        self.assertTrue(conn.proxy_speaker_ready.is_set())

    def test_message_type_is_speaker(self):
        self.assertEqual(SpeakerTextMessageHandler().message_type.value, "speaker")


def _build_dialogue():
    """构造含 <context> 分界 + 对话历史的 Dialogue(用于测 current_speaker 注入)"""
    d = Dialogue()
    d.put(Message(role="system", content=(
        "你是小智\n<context>\n- 今天日期：2026-07-12\n- 当前时间：10:00\n</context>\n<memory>\n</memory>")))
    d.put(Message(role="user", content="你好"))
    d.put(Message(role="assistant", content="你好啊"))
    return d


class TestDialogueCurrentSpeaker(unittest.TestCase):
    """dialogue 注入 <current_speaker> 块到实时 user 段(B 方案核心:speaker→块)"""

    def test_current_speaker_in_realtime_user(self):
        """name+relationship → 块在实时 user 段,含姓名和关系"""
        d = _build_dialogue()
        msgs = d.get_llm_dialogue_with_memory(
            current_speaker={"name": "张三", "relationship": "爸爸"})
        cs = [m for m in msgs if "<current_speaker>" in m["content"]]
        self.assertEqual(len(cs), 1)
        self.assertEqual(cs[0]["role"], "user")  # 必须在实时 user 段
        self.assertIn("张三", cs[0]["content"])
        self.assertIn("爸爸", cs[0]["content"])

    def test_current_speaker_name_only(self):
        """仅 name → 块含姓名,无关系括号"""
        d = _build_dialogue()
        msgs = d.get_llm_dialogue_with_memory(current_speaker={"name": "李四"})
        cs = [m for m in msgs if "<current_speaker>" in m["content"]]
        self.assertEqual(len(cs), 1)
        self.assertIn("李四", cs[0]["content"])
        self.assertNotIn("（", cs[0]["content"])

    def test_no_current_speaker_no_block(self):
        """无 current_speaker → 不产生块"""
        d = _build_dialogue()
        msgs = d.get_llm_dialogue_with_memory()
        self.assertFalse(any("<current_speaker>" in m["content"] for m in msgs))


class _ConcreteASR(ASRProviderBase):
    """最小具体子类,用于测试 handle_voice_stop"""

    async def speech_to_text(self, opus_data, session_id, audio_format="opus",
                             artifacts=None):
        return "", None


class TestHandleVoiceStopExternal(unittest.IsolatedAsyncioTestCase):
    """handle_voice_stop(B 方案):speaker 写入 conn.current_speaker,enhanced_text 不含 speaker"""

    async def _run(self, conn, raw_text="你好"):
        """跑 handle_voice_stop,返回 (conn, enhanced_text)"""
        asr = _ConcreteASR()
        asr.speech_to_text_wrapper = AsyncMock(return_value=(raw_text, None))
        with patch("core.providers.asr.base.startToChat", new=AsyncMock()) as mock_chat, \
             patch("core.providers.asr.base.enqueue_asr_report"):
            await asr.handle_voice_stop(conn, [b"fake-audio"])
        self.assertTrue(mock_chat.called, "startToChat 未被调用")
        return conn, mock_chat.call_args.args[1]

    async def test_external_speaker_into_current_speaker(self):
        """external + speaker 帧 → conn.current_speaker = 帧内容;enhanced_text 纯文本"""
        conn = _mock_conn(proxy_speaker={"name": "张三", "relationship": "爸爸"})
        conn, enhanced = await self._run(conn)
        self.assertEqual(conn.current_speaker,
                         {"name": "张三", "relationship": "爸爸"})
        self.assertEqual(enhanced, "你好")  # 纯文本,不再塞 speaker JSON
        self.assertNotIn("speaker", enhanced)

    async def test_external_name_only(self):
        """external + 仅 name → current_speaker = {name}"""
        conn = _mock_conn(proxy_speaker={"name": "李四"})
        conn, enhanced = await self._run(conn)
        self.assertEqual(conn.current_speaker, {"name": "李四"})

    async def test_external_timeout_no_speaker(self):
        """external + speaker 帧未到(超时)→ current_speaker = None"""
        conn = _mock_conn(proxy_speaker=None)  # event 未 set → wait_for 超时
        conn, enhanced = await self._run(conn)
        self.assertIsNone(conn.current_speaker)

    async def test_non_external_uses_voiceprint_provider(self):
        """非 external → VoiceprintProvider 结果写入 current_speaker"""
        vp = MagicMock()
        vp.identify_speaker = AsyncMock(return_value="王五")
        conn = _mock_conn(external=False, voiceprint_provider=vp)
        conn, enhanced = await self._run(conn)
        self.assertEqual(conn.current_speaker, {"name": "王五"})
        vp.identify_speaker.assert_awaited_once()
        self.assertEqual(enhanced, "你好")


if __name__ == "__main__":
    unittest.main(verbosity=2)
