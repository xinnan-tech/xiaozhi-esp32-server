"""提示词里的天气内容

天气有两条路进模型：工具调用那条走插件，提示词那条走 {weather_info} 占位符。
这条用例盯的是占位符那条：凭据没配好时它得给用户一句说明，不能留空让模型
自己编天气；取到的报告和失败提示也不能被塞进长缓存。
"""
from __future__ import annotations

import asyncio
import threading
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[3]

# 真插件没配凭据时给用户的提示语，里面带着给开发者看的文档路径。
# 提示词里不能出现这个路径，模型会照着念给终端用户
CREDENTIAL_HINT = "尚未配置和风天气 api_key，请参考 docs/weather-integration.md 申请后填入"
WEATHER_REPORT = "您查询的位置是：北京\n\n当前天气: 晴\n"
FAILURE_MESSAGE = "暂时查不到 北京 的天气（城市未找到或天气服务不可用），请稍后再试"


@pytest.fixture(autouse=True)
def _config_file():
    """import 链路要 data/.config.yaml 在场，缺了就现造一个空的"""
    config_file = _PROJECT_ROOT / "data" / ".config.yaml"
    if not config_file.exists():
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text("{}\n", encoding="utf-8")
    yield


class _FakeLoop:
    """给 _get_weather_info 用的假事件循环

    <p>
    那边用 call_soon_threadsafe 提交协程，这里起一个真循环在后台线程里跑，
    协程里的代码原样执行。
    """

    def __init__(self):
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()

    def call_soon_threadsafe(self, callback):
        self._loop.call_soon_threadsafe(callback)

    def close(self):
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=5)
        self._loop.close()


class _FakeConn:
    def __init__(self, loop, api_key: str):
        self.loop = loop
        self.config = {
            "plugins": {
                "get_weather": {
                    "api_key": api_key,
                    "api_host": "example-host",
                }
            }
        }
        self.client_ip = "1.2.3.4"
        self.device_id = "test-device"


def _install_fake_plugin(monkeypatch, responses=None):
    """把真插件换成假的：按有没有 api_key 走两种返回

    <p>
    responses 给了就按顺序回，回完最后一条就一直回最后一条。返回调用次数，
    用例要看插件被调了几次。
    """
    import plugins_func.functions.get_weather as weather_module
    from plugins_func.register import Action, ActionResponse

    calls = []

    async def _fake_get_weather(conn, location=None, lang="zh_CN"):
        api_key = str(
            conn.config.get("plugins", {}).get("get_weather", {}).get("api_key") or ""
        )
        calls.append(location)
        if not api_key.strip():
            return ActionResponse(Action.RESPONSE, None, CREDENTIAL_HINT)
        if responses:
            index = min(len(calls) - 1, len(responses) - 1)
            return responses[index]
        return ActionResponse(Action.REQLLM, WEATHER_REPORT, None)

    monkeypatch.setattr(weather_module, "get_weather", _fake_get_weather)
    return calls


@pytest.fixture
def _manager(tmp_path):
    """一个只带天气占位符的提示词管理器"""
    from core.utils.prompt_manager import PromptManager

    template = tmp_path / "prompt.txt"
    template.write_text("当前天气：{{weather_info}}", encoding="utf-8")
    return PromptManager({"prompt_template": str(template)})


@pytest.fixture
def _cache():
    """全局缓存，测试之间要清干净"""
    from core.utils.cache.manager import cache_manager, CacheType

    cache_manager.clear(CacheType.WEATHER)
    cache_manager.clear(CacheType.LOCATION)
    yield cache_manager
    cache_manager.clear(CacheType.WEATHER)
    cache_manager.clear(CacheType.LOCATION)


def _build_prompt(manager, conn):
    """走一遍真实的两步：先更新上下文，再拼提示词"""
    manager.update_context_info(conn, conn.client_ip)
    return manager.build_enhanced_prompt("你是助手", conn.device_id, conn.client_ip)


def test_unconfigured_weather_gives_notice_and_caches_nothing(
    monkeypatch, _manager, _cache
):
    """凭据没配好：提示词里要有说明，缓存里不能留下空条目"""
    from core.utils.cache.manager import CacheType

    _install_fake_plugin(monkeypatch)
    loop = _FakeLoop()
    conn = _FakeConn(loop, api_key="")
    _cache.set(CacheType.LOCATION, conn.client_ip, "北京")

    try:
        prompt = _build_prompt(_manager, conn)
    finally:
        loop.close()

    assert "未配置" in prompt
    # 给开发者的文档路径不能进提示词，模型会照着念给终端用户
    assert "docs/weather-integration.md" not in prompt
    # 天气内容不能是空的，空着模型会自己编一个
    assert prompt.strip() != "当前天气："
    # 空结果不写缓存
    assert _cache.get(CacheType.WEATHER, "北京") is None


@pytest.mark.parametrize("stale", [None, ""])
def test_empty_cached_entry_is_cleared_and_weather_is_fetched_again(
    monkeypatch, _manager, _cache, stale
):
    """缓存里已经有空条目时，配好凭据后下一次就该出天气"""
    from core.utils.cache.manager import CacheType

    calls = _install_fake_plugin(monkeypatch)
    loop = _FakeLoop()
    conn = _FakeConn(loop, api_key="not-a-real-key")
    _cache.set(CacheType.LOCATION, conn.client_ip, "北京")
    _cache.set(CacheType.WEATHER, "北京", stale)

    try:
        prompt = _build_prompt(_manager, conn)
    finally:
        loop.close()

    assert "当前天气: 晴" in prompt
    # 存量空条目被清掉了，没有留在缓存里
    assert _cache.get(CacheType.WEATHER, "北京") is None
    assert len(calls) == 1


def test_failed_weather_is_not_cached_and_is_fetched_again(
    monkeypatch, _manager, _cache
):
    """插件说查不到天气时，那句话不能进长缓存，下一次要重新取"""
    from core.utils.cache.manager import CacheType
    from plugins_func.register import Action, ActionResponse

    calls = _install_fake_plugin(
        monkeypatch,
        responses=[
            ActionResponse(Action.REQLLM, FAILURE_MESSAGE, None),
            ActionResponse(Action.REQLLM, WEATHER_REPORT, None),
        ],
    )
    loop = _FakeLoop()
    conn = _FakeConn(loop, api_key="not-a-real-key")
    _cache.set(CacheType.LOCATION, conn.client_ip, "北京")

    try:
        first_prompt = _build_prompt(_manager, conn)
        # 失败提示进提示词，用户能听到「暂时查不到」
        assert "暂时查不到" in first_prompt
        # 但它不能被存进 8 小时那档缓存，不然网络恢复了就出不来天气
        assert _cache.get(CacheType.WEATHER, "北京") is None

        second_prompt = _build_prompt(_manager, conn)
    finally:
        loop.close()

    # 下一次重新取，插件被调了两次
    assert len(calls) == 2
    assert "当前天气: 晴" in second_prompt


def test_configured_weather_report_goes_to_placeholder(
    monkeypatch, _manager, _cache
):
    """凭据齐全：报告照旧进占位符，缓存由插件那边管"""
    from core.utils.cache.manager import CacheType

    _install_fake_plugin(monkeypatch)
    loop = _FakeLoop()
    conn = _FakeConn(loop, api_key="not-a-real-key")
    _cache.set(CacheType.LOCATION, conn.client_ip, "北京")

    try:
        prompt = _build_prompt(_manager, conn)
    finally:
        loop.close()

    assert "当前天气: 晴" in prompt
    assert "未配置" not in prompt
    # 提示词这一侧不再自己存一份，成功那份由插件按 8 小时存
    assert _cache.get(CacheType.WEATHER, "北京") is None
