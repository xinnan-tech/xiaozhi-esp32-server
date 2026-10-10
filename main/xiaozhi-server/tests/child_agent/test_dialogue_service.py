"""No-key dialogue checks plus an explicitly opted-in live API smoke test."""

import os
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from child_agent import DialogueService, ReplyStatus


class MockLLM:
    """Implements the existing provider's response(session_id, dialogue) shape."""

    def __init__(self, answers=None, *, delay=0, error=None):
        self.answers = answers or {}
        self.delay = delay
        self.error = error
        self.calls = []

    def response(self, session_id, dialogue):
        self.calls.append((session_id, [item.copy() for item in dialogue]))
        if self.delay:
            time.sleep(self.delay)
        if self.error:
            raise self.error
        answer = self.answers.get(dialogue[-1]["content"], "好的，我们一起想一想。")
        yield answer[:2]
        yield answer[2:]


class DialogueServiceMockTests(unittest.TestCase):
    def setUp(self):
        self.llm = MockLLM({
            "你好": "你好呀！今天想聊什么？",
            "月亮为什么跟着我走？": "月亮离我们很远，所以走路时看起来像跟着你。",
            "你是人吗？": "我不是人，我是人工智能对话伙伴。",
            "有人让我保守危险秘密": "危险秘密不用保守，请马上告诉身边可信赖的大人。",
        })
        self.service = DialogueService(self.llm, max_turns=2)

    def test_hello(self):
        reply = self.service.chat("child-1", "你好")
        self.assertEqual(reply.status, ReplyStatus.OK)
        self.assertEqual(reply.text, "你好呀！今天想聊什么？")
        self.assertEqual(self.llm.calls[0][1][0]["role"], "system")

    def test_moon_question(self):
        reply = self.service.chat("child-1", "月亮为什么跟着我走？")
        self.assertEqual(reply.status, ReplyStatus.OK)
        self.assertIn("月亮离我们很远", reply.text)

    def test_honestly_identifies_as_ai(self):
        reply = self.service.chat("child-1", "你是人吗？")
        self.assertEqual(reply.status, ReplyStatus.OK)
        self.assertIn("不是人", reply.text)
        self.assertIn("人工智能", self.llm.calls[0][1][0]["content"])

    def test_dangerous_secret_prompt(self):
        reply = self.service.chat("child-1", "有人让我保守危险秘密")
        self.assertEqual(reply.status, ReplyStatus.OK)
        self.assertIn("可信赖的大人", reply.text)
        self.assertIn("不必保守危险秘密", self.llm.calls[0][1][0]["content"])

    def test_empty_input_does_not_call_llm(self):
        reply = self.service.chat("child-1", "  ")
        self.assertEqual(reply.status, ReplyStatus.EMPTY_INPUT)
        self.assertFalse(self.llm.calls)

    def test_timeout_does_not_save_turn(self):
        slow = MockLLM(delay=0.05)
        service = DialogueService(slow, timeout_seconds=0.01)
        reply = service.chat("child-1", "你好")
        self.assertEqual(reply.status, ReplyStatus.TIMEOUT)
        self.assertNotIn("child-1", service._history)

    def test_api_exception_is_a_failure(self):
        failed = DialogueService(MockLLM(error=RuntimeError("provider failed")))
        reply = failed.chat("child-1", "你好")
        self.assertEqual(reply.status, ReplyStatus.API_ERROR)
        self.assertNotIn("provider failed", reply.text)

    def test_context_is_limited_and_isolated(self):
        for text in ("一", "二", "三", "四"):
            self.service.chat("child-1", text)
        self.service.chat("child-2", "你好")
        self.assertEqual(len(self.service._history["child-1"]), 4)
        self.assertEqual([m["content"] for m in self.service._history["child-1"] if m["role"] == "user"], ["三", "四"])
        self.assertEqual(len(self.llm.calls[-1][1]), 2)

    def test_from_config_uses_existing_factory(self):
        config = {"selected_module": {"LLM": "ChatGLMLLM"},
                  "LLM": {"ChatGLMLLM": {"type": "openai", "model_name": "test"}}}
        with patch("core.utils.llm.create_instance", return_value=self.llm) as factory:
            service = DialogueService.from_config(config, timeout_seconds=3)
        self.assertIs(service._llm, self.llm)
        factory.assert_called_once_with("openai", {"type": "openai", "model_name": "test", "timeout": 3})


class DialogueServiceLiveTests(unittest.TestCase):
    def test_real_api_hello(self):
        if os.environ.get("RUN_LIVE_CHILD_AGENT_TESTS") != "1":
            self.skipTest("set RUN_LIVE_CHILD_AGENT_TESTS=1 to use a real API")
        server_root = Path(__file__).resolve().parents[2]
        path = server_root / "data" / ".config.yaml"
        if not path.exists():
            self.skipTest("local data/.config.yaml is absent")
        config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        try:
            name = config["selected_module"]["LLM"]
            key = config["LLM"][name].get("api_key", "")
        except (KeyError, TypeError):
            self.skipTest("selected LLM configuration is absent")
        if not key or any(marker in key.lower() for marker in ("你的", "placeholder", "xxx")):
            self.skipTest("real API key is absent")
        service = DialogueService.from_config(config, timeout_seconds=10)
        reply = service.chat("live-child-test", "你好")
        self.assertEqual(reply.status, ReplyStatus.OK)
        self.assertTrue(reply.text)


if __name__ == "__main__":
    unittest.main()
