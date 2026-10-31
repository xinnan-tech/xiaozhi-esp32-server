"""把原版的统一工具处理器（UnifiedToolHandler）接给语音进语音出的模型。

模型拿到的工具清单来自 conn.func_handler.get_functions()：服务端插件、server_mcp、设备 MCP、MCP 接入点在那里已经合成一份，
格式是 chat-completions 的 {"type": "function", "function": {name, description, parameters}}；Realtime 要的是拍平的
{"type": "function", "name", "description", "parameters"}。执行走 conn.func_handler.handle_llm_function_call，拿到
ActionResponse 后翻成一段交给模型的文字（模型据此开口）。

接线层自己做、不改原版工具包：白名单（tools_allow，空 = 全部）、每会话每分钟调用次数上限、request_id 与耗时日志。
"""
from __future__ import annotations

import time
import uuid
from collections import deque
from typing import Any, Iterable

from plugins_func.register import Action

TAG = __name__


def to_realtime_tools(functions: Iterable[dict[str, Any]] | None, allow: set[str] | None = None) -> list[dict[str, Any]]:
    """chat-completions 工具描述 → Realtime 工具描述；allow 非空时只保留名单内的。"""
    out: list[dict[str, Any]] = []
    for f in functions or []:
        fn = f.get("function") if isinstance(f, dict) else None
        if not isinstance(fn, dict) or not fn.get("name"):
            continue
        name = str(fn["name"])
        if allow and name not in allow:
            continue
        tool = {"type": "function", "name": name,
                "description": str(fn.get("description") or ""),
                "parameters": fn.get("parameters") or {"type": "object", "properties": {}}}
        out.append(tool)
    return out


class ToolRunner:
    """给一条连接用的工具执行器。"""

    def __init__(self, conn, logger, per_minute: int = 12, allow: Iterable[str] | None = None):
        self.conn = conn
        self.logger = logger
        self.per_minute = int(per_minute)
        self.allow = {str(a) for a in allow} if allow else set()
        self._recent: deque[float] = deque()
        self.calls = 0

    def allowed(self, name: str) -> bool:
        return not self.allow or name in self.allow

    def _over_rate(self) -> bool:
        now = time.monotonic()
        while self._recent and now - self._recent[0] > 60:
            self._recent.popleft()
        if len(self._recent) >= self.per_minute:
            return True
        self._recent.append(now)
        return False

    async def run(self, name: str, arguments: str | dict | None) -> str:
        """执行一个工具调用，返回交给模型的文字。永不抛异常。"""
        rid = uuid.uuid4().hex[:8]
        t0 = time.monotonic()
        self.calls += 1
        if not name:
            return "工具名为空，无法执行。"
        if not self.allowed(name):
            self.logger.bind(tag=TAG).warning(f"tool {name} rid={rid} 不在白名单，拒绝")
            return f"工具 {name} 不允许使用。"
        if self._over_rate():
            self.logger.bind(tag=TAG).warning(f"tool {name} rid={rid} 超过每分钟 {self.per_minute} 次上限，拒绝")
            return "工具调用太频繁，请稍后再试。"
        handler = getattr(self.conn, "func_handler", None)
        if handler is None:
            return "服务器还没准备好工具，请稍后再试。"
        try:
            resp = await handler.handle_llm_function_call(
                self.conn, {"name": name, "arguments": arguments if arguments is not None else "{}"}
            )
            text, action = self._to_text(resp)
        except Exception as e:  # noqa: BLE001
            text, action = f"工具 {name} 执行出错：{type(e).__name__}", "EXCEPTION"
        ms = round((time.monotonic() - t0) * 1000)
        self.logger.bind(tag=TAG).info(f"tool {name} rid={rid} {action} {ms} ms, output {len(text)} chars")
        return text

    @staticmethod
    def _to_text(resp) -> tuple[str, str]:
        if resp is None:
            return "工具没有返回结果。", "NONE"
        action = getattr(resp, "action", None)
        result = getattr(resp, "result", None)
        response = getattr(resp, "response", None)
        name = getattr(action, "name", str(action))
        if action == Action.RESPONSE:
            return str(response or result or "已完成。"), name
        if action == Action.REQLLM:
            return str(result or response or "已完成，请据此回答用户。"), name
        if action in (Action.NONE, Action.RECORD):
            return str(result or response or "已执行。"), name
        if action == Action.NOTFOUND:
            return "没有这个工具。", name
        if action == Action.ERROR:
            return f"工具出错：{response or result or '未知错误'}", name
        return str(response or result or "已完成。"), name
