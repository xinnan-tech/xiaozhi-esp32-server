"""MCP 接入点 tools/call 通过 _meta 携带说话人，不改工具参数。"""
import json

import pytest

from core.providers.tools.mcp_endpoint.mcp_speaker import (
    build_mcp_endpoint_tool_payload,
    should_forward_speaker,
    speaker_call_meta,
)
from core.utils.voiceprint_provider import UNKNOWN_SPEAKER_NAME


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
    def __init__(self, config=None, speaker_id="test1", speaker_name="张三"):
        self.mcp_endpoint_client = _Client()
        self.config = {} if config is None else config
        self.current_speaker_id = speaker_id
        self.current_speaker = speaker_name


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
        conn, "HassTurnOn", arguments
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
    await executor_mod.MCPEndpointExecutor(conn).execute(conn, "HassTurnOn", {"area": "客厅"})
    assert captured["meta"] is None


@pytest.mark.asyncio
async def test_executor_omits_meta_for_unknown_speaker(monkeypatch):
    from core.providers.tools.mcp_endpoint import mcp_endpoint_executor as executor_mod

    captured = {}

    async def fake_call(client, tool_name, args_str="{}", timeout=30, meta=None):
        captured["meta"] = meta
        return "done"

    monkeypatch.setattr(executor_mod, "call_mcp_endpoint_tool", fake_call)
    conn = _Conn(speaker_id=None, speaker_name=UNKNOWN_SPEAKER_NAME)
    await executor_mod.MCPEndpointExecutor(conn).execute(conn, "HassTurnOn", {})
    assert captured["meta"] is None
