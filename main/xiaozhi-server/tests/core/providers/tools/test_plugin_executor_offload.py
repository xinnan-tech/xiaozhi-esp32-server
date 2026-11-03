"""服务端插件执行器：同步插件函数在线程池里跑，不卡事件循环；async 插件照常 await；异常变成 ERROR 响应。"""
from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace

from core.providers.tools.server_plugins.plugin_executor import ServerPluginExecutor
from plugins_func.register import Action, ActionResponse, ToolType, all_function_registry


def _register(name, func, tool_type):
    item = SimpleNamespace(name=name, func=func, type=tool_type, description={})
    all_function_registry[name] = item
    return item


def test_sync_plugin_runs_off_loop_and_async_plugin_is_awaited():
    conn = SimpleNamespace(config={})

    async def paced_sleep(delay):
        # 不能用 asyncio.sleep 计时：conftest 在 mock 模式会把它换成不让出循环的桩，
        # 这里放到线程池里睡，保证 ticker 每拍都真正让出事件循环。
        await asyncio.get_running_loop().run_in_executor(None, time.sleep, delay)

    def slow_sync(conn_arg, entity_id):
        time.sleep(0.3)  # 模拟阻塞 IO
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
                    await paced_sleep(0.02)

            t = asyncio.create_task(ticker())
            r = await ex.execute(conn, "t_slow_sync", {"entity_id": "light.living"})
            t.cancel()
            assert r.action == Action.RESPONSE and r.response == "light.living 已打开"
            assert len(ticks) >= 5                      # 300 ms 里事件循环一直在转（没被 time.sleep 卡住）
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


def test_conn_passing_rules_and_compat_branches():
    """code 3/4/5 传 conn；WAIT/type=None 不传；同步函数返回协程会被兜底 await。"""
    conn = SimpleNamespace(config={})
    seen = {}

    def prompt_fn(conn_arg):
        seen["prompt"] = conn_arg
        return ActionResponse(Action.RESPONSE, None, "切角色")

    def wait_fn():
        seen["wait"] = True
        return ActionResponse(Action.RESPONSE, None, "等")

    def no_type_fn():
        seen["no_type"] = True
        return ActionResponse(Action.RESPONSE, None, "无类型")

    def sync_returns_coro(conn_arg):
        seen["coro"] = conn_arg

        async def inner():
            return ActionResponse(Action.RESPONSE, None, "协程兜底")

        return inner()

    _register("t_prompt", prompt_fn, ToolType.CHANGE_SYS_PROMPT)
    _register("t_wait", wait_fn, ToolType.WAIT)
    _register("t_no_type", no_type_fn, None)
    _register("t_sync_coro", sync_returns_coro, ToolType.SYSTEM_CTL)
    try:
        async def go():
            ex = ServerPluginExecutor(conn)
            r1 = await ex.execute(conn, "t_prompt", {})
            assert seen["prompt"] is conn and r1.response == "切角色"
            r2 = await ex.execute(conn, "t_wait", {})
            assert "wait" in seen and r2.response == "等"
            r3 = await ex.execute(conn, "t_no_type", {})
            assert "no_type" in seen and r3.response == "无类型"
            r4 = await ex.execute(conn, "t_sync_coro", {})
            assert seen["coro"] is conn and r4.response == "协程兜底"
        asyncio.run(go())
    finally:
        for n in ("t_prompt", "t_wait", "t_no_type", "t_sync_coro"):
            all_function_registry.pop(n, None)


def test_sync_plugin_uses_dedicated_pool():
    """同步插件必须跑在专用池上，不能用 asyncio 默认池（DNS 解析等共用默认池）。"""
    import threading

    conn = SimpleNamespace(config={})
    seen = {}

    def sync_fn():
        seen["thread"] = threading.current_thread().name
        return ActionResponse(Action.RESPONSE, None, "ok")

    _register("t_pool", sync_fn, ToolType.WAIT)
    try:
        async def go():
            ex = ServerPluginExecutor(conn)
            r = await ex.execute(conn, "t_pool", {})
            assert r.response == "ok"

        asyncio.run(go())
        assert seen["thread"].startswith("plugin"), seen["thread"]  # 专用池线程名前缀
    finally:
        all_function_registry.pop("t_pool", None)
