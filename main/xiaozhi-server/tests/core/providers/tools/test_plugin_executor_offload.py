"""服务端插件执行器：同步插件函数在线程池里跑，不卡事件循环；async 插件照常 await；异常变成 ERROR 响应。"""
from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace

from core.providers.tools.server_plugins.plugin_executor import ServerPluginExecutor
from plugins_func.register import Action, ActionResponse, ToolType, all_function_registry

_real_sleep = asyncio.tasks.sleep  # conftest 在 mock 模式把 asyncio.sleep 换成空函数


def _register(name, func, tool_type):
    item = SimpleNamespace(name=name, func=func, type=tool_type, description={})
    all_function_registry[name] = item
    return item


def test_sync_plugin_runs_off_loop_and_async_plugin_is_awaited(monkeypatch):
    monkeypatch.setattr(asyncio, "sleep", _real_sleep)
    conn = SimpleNamespace(config={})

    def slow_sync(conn_arg, entity_id):
        time.sleep(0.3)  # 模拟 requests 调 HA
        return ActionResponse(Action.RESPONSE, None, f"{entity_id} 已打开")

    async def fast_async(question):
        await asyncio.sleep(0)
        return ActionResponse(Action.REQLLM, f"答：{question}", None)

    def boom(conn_arg):
        raise RuntimeError("连不上")

    _register("t_slow_sync", slow_sync, ToolType.SYSTEM_CTL)
    _register("t_fast_async", fast_async, ToolType.WAIT)
    _register("t_boom", boom, ToolType.SYSTEM_CTL)
    try:
        async def go():
            ex = ServerPluginExecutor(conn)
            ticks = []

            async def ticker():
                while True:
                    ticks.append(time.monotonic())
                    await asyncio.sleep(0.02)

            t = asyncio.create_task(ticker())
            r = await ex.execute(conn, "t_slow_sync", {"entity_id": "light.living"})
            t.cancel()
            assert r.action == Action.RESPONSE and r.response == "light.living 已打开"
            assert len(ticks) >= 8                      # 300 ms 里事件循环一直在转（没被 time.sleep 卡住）
            r2 = await ex.execute(conn, "t_fast_async", {"question": "几点"})
            assert r2.action == Action.REQLLM and r2.result == "答：几点"
            r3 = await ex.execute(conn, "t_boom", {})
            assert r3.action == Action.ERROR and "连不上" in r3.response
            r4 = await ex.execute(conn, "t_missing", {})
            assert r4.action == Action.NOTFOUND
        asyncio.run(go())
    finally:
        for n in ("t_slow_sync", "t_fast_async", "t_boom"):
            all_function_registry.pop(n, None)
