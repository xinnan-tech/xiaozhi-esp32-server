"""MCP 接入点 tools/call 通过 _meta 携带说话人，不改工具参数。"""
import json

import pytest

from core.providers.tools.mcp_endpoint.mcp_speaker import (
    build_mcp_endpoint_tool_payload,
    should_forward_speaker,
    speaker_call_meta,
)
from core.utils.voiceprint_provider import UNKNOWN_SPEAKER_NAME, SpeakerIdentification


def test_meta_includes_id_and_name():
    assert speaker_call_meta(" test1 ", " 张三 ") == {
        "speakerId": "test1",
        "speakerName": "张三",
    }


def test_meta_omits_unknown_speaker_and_blank_id():
    assert speaker_call_meta(None, UNKNOWN_SPEAKER_NAME) is None
    assert speaker_call_meta("  ", "张三") == {"speakerName": "张三"}
    assert speaker_call_meta("test1", UNKNOWN_SPEAKER_NAME) == {"speakerId": "test1"}


def test_forwarding_defaults_on_and_can_be_disabled():
    assert should_forward_speaker(None) is True
    assert should_forward_speaker({}) is True
    assert should_forward_speaker({"mcp_forward_speaker": True}) is True
    assert should_forward_speaker({"mcp_forward_speaker": False}) is False
    # 字符串 false 可关闭；空值视为缺省开启
    assert should_forward_speaker({"mcp_forward_speaker": "false"}) is False
    assert should_forward_speaker({"mcp_forward_speaker": "False"}) is False
    assert should_forward_speaker({"mcp_forward_speaker": "0"}) is False
    assert should_forward_speaker({"mcp_forward_speaker": "true"}) is True
    assert should_forward_speaker({"mcp_forward_speaker": None}) is True
    # 空串按关闭处理，与 manager-api 的 Boolean.parseBoolean("") 一致
    assert should_forward_speaker({"mcp_forward_speaker": ""}) is False


def test_payload_adds_meta_without_touching_arguments():
    arguments = {"name": "灯"}
    payload = build_mcp_endpoint_tool_payload(
        7,
        "HassTurnOn",
        arguments,
        {"speakerId": "test1", "speakerName": "张三"},
    )
    assert payload["method"] == "tools/call"
    assert payload["params"]["arguments"] is arguments
    assert "speakerId" not in arguments
    assert payload["params"]["_meta"]["speakerId"] == "test1"


def test_payload_without_meta_matches_previous_shape():
    payload = build_mcp_endpoint_tool_payload(7, "calculator", {"a": 1})
    assert set(payload["params"]) == {"name", "arguments"}
    assert "_meta" not in payload["params"]


class _Client:
    async def is_ready(self):
        return True


class _Conn:
    def __init__(self, config=None):
        self.mcp_endpoint_client = _Client()
        self.config = {} if config is None else config


@pytest.mark.asyncio
async def test_executor_forwards_speaker_in_meta_only(monkeypatch):
    from core.providers.tools.mcp_endpoint import mcp_endpoint_executor as executor_mod

    captured = {}

    async def fake_call(client, tool_name, args_str="{}", timeout=30, meta=None):
        captured["tool_name"] = tool_name
        captured["args"] = args_str
        captured["meta"] = meta
        return "done"

    monkeypatch.setattr(executor_mod, "call_mcp_endpoint_tool", fake_call)
    arguments = {"area": "客厅"}
    conn = _Conn()
    result = await executor_mod.MCPEndpointExecutor(conn).execute(
        conn,
        "HassTurnOn",
        arguments,
        speaker=SpeakerIdentification("test1", "张三"),
    )

    assert json.loads(captured["args"]) == {"area": "客厅"}
    assert captured["meta"] == {"speakerId": "test1", "speakerName": "张三"}
    assert arguments == {"area": "客厅"}
    assert result.result == "done"


@pytest.mark.asyncio
async def test_executor_skips_meta_when_disabled(monkeypatch):
    from core.providers.tools.mcp_endpoint import mcp_endpoint_executor as executor_mod

    captured = {}

    async def fake_call(client, tool_name, args_str="{}", timeout=30, meta=None):
        captured["meta"] = meta
        return "done"

    monkeypatch.setattr(executor_mod, "call_mcp_endpoint_tool", fake_call)
    conn = _Conn(config={"mcp_forward_speaker": False})
    await executor_mod.MCPEndpointExecutor(conn).execute(
        conn,
        "HassTurnOn",
        {"area": "客厅"},
        speaker=SpeakerIdentification("test1", "张三"),
    )
    assert captured["meta"] is None


@pytest.mark.asyncio
async def test_executor_omits_meta_for_unknown_speaker(monkeypatch):
    from core.providers.tools.mcp_endpoint import mcp_endpoint_executor as executor_mod

    captured = {}

    async def fake_call(client, tool_name, args_str="{}", timeout=30, meta=None):
        captured["meta"] = meta
        return "done"

    monkeypatch.setattr(executor_mod, "call_mcp_endpoint_tool", fake_call)
    conn = _Conn()
    await executor_mod.MCPEndpointExecutor(conn).execute(
        conn,
        "HassTurnOn",
        {},
        speaker=SpeakerIdentification(None, UNKNOWN_SPEAKER_NAME),
    )
    assert captured["meta"] is None


@pytest.mark.asyncio
async def test_executor_reads_snapshot_not_conn_state(monkeypatch):
    """meta 取自快照，不受连接态影响。"""
    from core.providers.tools.mcp_endpoint import mcp_endpoint_executor as executor_mod

    captured = {}

    async def fake_call(client, tool_name, args_str="{}", timeout=30, meta=None):
        captured["meta"] = meta
        return "done"

    monkeypatch.setattr(executor_mod, "call_mcp_endpoint_tool", fake_call)
    conn = _Conn()
    await executor_mod.MCPEndpointExecutor(conn).execute(
        conn,
        "HassTurnOn",
        {},
        speaker=SpeakerIdentification("test1", "张三"),
    )
    assert captured["meta"] == {"speakerId": "test1", "speakerName": "张三"}
