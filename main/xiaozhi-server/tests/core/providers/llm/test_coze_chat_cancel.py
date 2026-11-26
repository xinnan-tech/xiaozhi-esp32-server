"""Coze provider 的会话收尾测试。

覆盖 #2076：客户端打断后上一轮 chat 还占着 coze 会话，下一轮请求撞上
4016 Conversation occupied，整轮对话直接卡死。

- 客户端打断 → 生成器被提前关闭 → 主动取消上游 chat，但保留 conversation_id
  （上下文不丢）
- 正常说完 → 不需要取消
- 真的撞上 4016 → 清掉本地会话 id，下一轮重新建会话，不再一直卡住
"""

from types import SimpleNamespace

import pytest
from cozepy import ChatEventType

from core.providers.llm.coze import coze as coze_module
from core.providers.llm.coze.coze import LLMProvider as CozeProvider

CONVERSATION_ID = "conv-new"


def _delta(content):
    return SimpleNamespace(
        event=ChatEventType.CONVERSATION_MESSAGE_DELTA,
        chat=None,
        message=SimpleNamespace(content=content),
    )


def _chat_created(chat_id="chat-1"):
    return SimpleNamespace(
        event=ChatEventType.CONVERSATION_CHAT_CREATED,
        chat=SimpleNamespace(id=chat_id),
        message=None,
    )


def _chat_completed(chat_id="chat-1"):
    return SimpleNamespace(
        event=ChatEventType.CONVERSATION_CHAT_COMPLETED,
        chat=SimpleNamespace(id=chat_id),
        message=None,
    )


def _install_fake_coze(monkeypatch, events, error=None):
    """把 coze 模块里的 Coze 换成假实现，返回记录调用状态的 dict"""
    state = {"cancelled": [], "created": []}

    class FakeChat:
        def stream(self, **kwargs):
            for event in events:
                yield event
            if error is not None:
                raise error

        def cancel(self, conversation_id, chat_id):
            state["cancelled"].append((conversation_id, chat_id))

    class FakeConversations:
        def create(self, messages=None):
            state["created"].append(messages)
            return SimpleNamespace(id=CONVERSATION_ID)

    class FakeCoze:
        def __init__(self, auth=None, base_url=None):
            self.chat = FakeChat()
            self.conversations = FakeConversations()

    monkeypatch.setattr(coze_module, "Coze", FakeCoze)
    return state


def _provider():
    return CozeProvider(
        {
            "personal_access_token": "pat-test",
            "bot_id": "bot-1",
            "user_id": "user-1",
        }
    )


def _dialogue():
    return [{"role": "user", "content": "你好"}]


def test_completed_chat_is_not_cancelled(monkeypatch):
    state = _install_fake_coze(
        monkeypatch, [_chat_created(), _delta("你好"), _chat_completed()]
    )

    provider = _provider()
    result = list(provider.response("s1", _dialogue()))

    assert result == ["你好"]
    assert state["cancelled"] == []


def test_interrupted_chat_is_cancelled(monkeypatch):
    state = _install_fake_coze(monkeypatch, [_chat_created(), _delta("你好")])

    provider = _provider()
    responses = provider.response("s1", _dialogue())
    assert next(responses) == "你好"

    # 客户端打断：core/connection.py 跳出流式循环后生成器被关闭
    responses.close()

    assert state["cancelled"] == [(CONVERSATION_ID, "chat-1")]


def test_interrupted_chat_keeps_conversation_id(monkeypatch):
    """取消上游 chat，但不能把会话 id 丢掉，否则上下文就没了"""
    _install_fake_coze(monkeypatch, [_chat_created(), _delta("你好")])

    provider = _provider()
    responses = provider.response("s1", _dialogue())
    next(responses)
    responses.close()

    assert provider.session_conversation_map["s1"] == CONVERSATION_ID


def test_occupied_conversation_is_reset(monkeypatch):
    error = Exception(
        'error event: {"code":4016,"msg":"Conversation occupied: Another chat '
        'is currently active."}'
    )
    _install_fake_coze(monkeypatch, [_chat_created()], error=error)

    provider = _provider()
    provider.session_conversation_map["s1"] = "conv-old"

    with pytest.raises(Exception):
        list(provider.response("s1", _dialogue()))

    # 本地记的会话 id 被清掉，下一轮会重新建会话
    assert "s1" not in provider.session_conversation_map


def test_other_errors_keep_conversation_id(monkeypatch):
    error = Exception("error event: {\"code\":5000}")
    _install_fake_coze(monkeypatch, [_chat_created()], error=error)

    provider = _provider()
    provider.session_conversation_map["s1"] = "conv-old"

    with pytest.raises(Exception):
        list(provider.response("s1", _dialogue()))

    assert provider.session_conversation_map["s1"] == "conv-old"


def test_next_turn_cancels_leftover_chat(monkeypatch):
    """上一轮遗留的 chat，这一轮开始前先取消掉，不会撞上 4016"""
    state = _install_fake_coze(monkeypatch, [_chat_created(), _delta("你好")])

    provider = _provider()
    # 模拟「上一轮被打断、没走完收尾」：会话 id 还留着，chat 还占着
    provider.session_conversation_map["s1"] = CONVERSATION_ID
    provider.pending_chats["s1"] = (CONVERSATION_ID, "chat-stale")

    list(provider.response("s1", _dialogue()))

    assert (CONVERSATION_ID, "chat-stale") in state["cancelled"]
    # 会话 id 保留，上下文不丢
    assert provider.session_conversation_map["s1"] == CONVERSATION_ID


def test_completed_chat_leaves_no_pending(monkeypatch):
    _install_fake_coze(
        monkeypatch, [_chat_created(), _delta("你好"), _chat_completed()]
    )

    provider = _provider()
    list(provider.response("s1", _dialogue()))

    assert provider.pending_chats == {}
