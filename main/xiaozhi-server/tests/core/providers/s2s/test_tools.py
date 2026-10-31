"""S2S 工具接线：chat-completions → Realtime 工具描述、ActionResponse → 文字、白名单、限频、异常不外泄。"""
from __future__ import annotations

import asyncio

from config.logger import setup_logging
from core.providers.s2s.tools import ToolRunner, to_realtime_tools
from plugins_func.register import Action, ActionResponse

FUNCS = [
    {"type": "function", "function": {"name": "hass_state", "description": "控制设备",
                                      "parameters": {"type": "object", "properties": {"entity_id": {"type": "string"}}}}},
    {"type": "function", "function": {"name": "get_weather", "description": "天气"}},
    {"type": "function", "function": {"description": "没有名字，应被丢掉"}},
    "不是字典",
]


def test_to_realtime_tools_flattens_and_filters():
    tools = to_realtime_tools(FUNCS)
    assert [t["name"] for t in tools] == ["hass_state", "get_weather"]
    assert tools[0] == {"type": "function", "name": "hass_state", "description": "控制设备",
                        "parameters": {"type": "object", "properties": {"entity_id": {"type": "string"}}}}
    assert tools[1]["parameters"] == {"type": "object", "properties": {}}   # 没给 parameters 的补一个空对象
    assert [t["name"] for t in to_realtime_tools(FUNCS, {"get_weather"})] == ["get_weather"]
    assert to_realtime_tools(None) == []


class _Handler:
    def __init__(self, resp=None, raise_exc=False):
        self.resp, self.raise_exc, self.calls = resp, raise_exc, []

    async def handle_llm_function_call(self, conn, data):
        self.calls.append(data)
        if self.raise_exc:
            raise RuntimeError("boom")
        return self.resp


class _Conn:
    def __init__(self, handler):
        self.func_handler = handler


def _run(runner, name, args="{}"):
    return asyncio.run(runner.run(name, args))


def test_action_mapping_and_arguments_passthrough():
    log = setup_logging()
    h = _Handler(ActionResponse(Action.RESPONSE, None, "客厅灯已打开"))
    r = ToolRunner(_Conn(h), log)
    assert _run(r, "hass_state", '{"entity_id": "light.living"}') == "客厅灯已打开"
    assert h.calls[0] == {"name": "hass_state", "arguments": '{"entity_id": "light.living"}'}
    assert _run(ToolRunner(_Conn(_Handler(ActionResponse(Action.REQLLM, "今天晴 20 度", None))), log), "get_weather") == "今天晴 20 度"
    assert _run(ToolRunner(_Conn(_Handler(ActionResponse(Action.NOTFOUND))), log), "x") == "没有这个工具。"
    assert _run(ToolRunner(_Conn(_Handler(ActionResponse(Action.ERROR, None, "连不上"))), log), "x") == "工具出错：连不上"
    assert _run(ToolRunner(_Conn(_Handler(ActionResponse(Action.NONE))), log), "x") == "已执行。"
    assert _run(ToolRunner(_Conn(_Handler(None)), log), "x") == "工具没有返回结果。"


def test_whitelist_rate_limit_and_exceptions():
    log = setup_logging()
    h = _Handler(ActionResponse(Action.RESPONSE, None, "ok"))
    r = ToolRunner(_Conn(h), log, per_minute=2, allow=["hass_state"])
    assert _run(r, "get_weather") == "工具 get_weather 不允许使用。" and h.calls == []
    assert _run(r, "hass_state") == "ok" and _run(r, "hass_state") == "ok"
    assert _run(r, "hass_state") == "工具调用太频繁，请稍后再试。" and len(h.calls) == 2
    assert _run(ToolRunner(_Conn(_Handler(raise_exc=True)), log), "hass_state").startswith("工具 hass_state 执行出错")
    assert _run(ToolRunner(_Conn(None), log), "hass_state") == "服务器还没准备好工具，请稍后再试。"
    assert _run(r, "") == "工具名为空，无法执行。"
