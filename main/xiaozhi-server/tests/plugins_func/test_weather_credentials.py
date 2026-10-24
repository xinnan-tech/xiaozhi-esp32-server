"""天气插件的凭据、健壮性和报告格式测试。

接口一律换成假客户端，不碰网络。
"""
import datetime
import os
import time
from datetime import date as _date
from datetime import timedelta as _timedelta
from datetime import timezone as _timezone

import httpx
import pytest
from bs4 import BeautifulSoup

from plugins_func.functions import get_weather as weather_module
from plugins_func.register import Action


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self.payload = payload
        self.text = text

    def json(self):
        return self.payload


class FakeAsyncClient:
    """顶替 httpx.AsyncClient，把建客户端时的参数记下来"""

    requests = []
    responder = None
    init_kwargs = {}

    def __init__(self, *args, **kwargs):
        FakeAsyncClient.init_kwargs = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def get(self, url, params=None, headers=None):
        FakeAsyncClient.requests.append({"url": url, "params": params})
        return FakeAsyncClient.responder(url, params)


@pytest.fixture
def fake_http(monkeypatch):
    FakeAsyncClient.requests = []
    FakeAsyncClient.responder = lambda url, params: FakeResponse(payload={"code": "200"})
    FakeAsyncClient.init_kwargs = {}
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    return FakeAsyncClient


@pytest.fixture(autouse=True)
def clear_weather_cache():
    """天气缓存是全局的，清一下免得上一条用例的结果串到下一条"""
    from core.utils.cache.manager import cache_manager, CacheType

    cache_manager.clear(CacheType.WEATHER)
    yield
    cache_manager.clear(CacheType.WEATHER)


class FakeConn:
    def __init__(self, plugins=None):
        self.config = {"plugins": plugins or {}}
        self.client_ip = None


def _today():
    return datetime.date.today()


def _web_page(date_text, temp_high="13°", temp_low="9°", current_time=None):
    """照着和风天气网页的样子拼一段，解析要的就是这些结构和写法"""
    time_block = (
        f'<div class="current-weather__bg"><span class="current-time">{current_time}</span></div>'
        if current_time
        else ""
    )
    return f"""
    <html>
      <h1 class="c-submenu__location">杭州市</h1>
      <div class="c-city-weather-current">
        <div class="current-abstract">多云</div>
        <div class="current-basic">
          <div class="current-basic___item">4级 西北风</div>
          <div class="current-basic___item">97% 相对湿度</div>
          <div class="current-basic___item">13° 体感温度</div>
          <div class="current-basic___item">9km 能见度</div>
          <div class="current-basic___item">0.0mm 降水量</div>
          <div class="current-basic___item">1009hPa 大气压</div>
        </div>
      </div>
      {time_block}
      <div class="city-forecast-tabs">
        <div class="city-forecast-tabs__row">
          <div class="date-bg">
            <span class="date">{date_text}</span>
            <img class="icon" src="https://static.qweather.com/img/common/icon/202106d/306.png">
          </div>
          <div class="tmp-cont">
            <span class="temp">{temp_high}</span>
            <span class="temp">{temp_low}</span>
          </div>
        </div>
      </div>
    </html>
    """


# ---------------------------------------------------------------------------
# 凭据
# ---------------------------------------------------------------------------


class RecordingLogger:
    """把日志收下来，好断言告警里带着文档路径"""

    def __init__(self):
        self.messages = []

    def bind(self, **kwargs):
        return self

    def _record(self, message, *args, **kwargs):
        self.messages.append(str(message))

    warning = _record
    error = _record
    info = _record
    debug = _record


async def test_missing_api_key_points_at_the_application_doc():
    response = await weather_module.get_weather(
        FakeConn({"get_weather": {"api_host": "h"}}), location="没配密钥市"
    )

    assert response.action == Action.RESPONSE
    assert response.response == (
        "尚未配置和风天气 api_key，请参考 docs/weather-integration.md 申请后填入"
    )


async def test_missing_api_host_points_at_the_application_doc():
    response = await weather_module.get_weather(
        FakeConn({"get_weather": {"api_key": "k"}}), location="没配主机市"
    )

    assert response.action == Action.RESPONSE
    assert response.response == (
        "尚未配置和风天气 api_host，请参考 docs/weather-integration.md 申请后填入"
    )


async def test_blank_api_key_counts_as_missing():
    response = await weather_module.get_weather(
        FakeConn({"get_weather": {"api_key": "   ", "api_host": "h"}}), location="空密钥市"
    )

    assert "尚未配置和风天气 api_key" in response.response


async def test_missing_credentials_are_logged_with_the_doc_path(monkeypatch):
    """日志里得写清楚缺哪一项、去哪儿申请，开发看日志就能定位"""
    recorder = RecordingLogger()
    monkeypatch.setattr(weather_module, "logger", recorder)

    await weather_module.get_weather(
        FakeConn({"get_weather": {"api_host": "h"}}), location="没配密钥市"
    )

    assert recorder.messages, "凭据缺失时一条日志都没有"
    assert any(
        "api_key" in message and "docs/weather-integration.md" in message
        for message in recorder.messages
    ), f"告警里没写清楚缺哪一项、文档在哪儿：{recorder.messages}"


async def test_missing_credentials_are_not_cached():
    """凭据缺失的提示不能进缓存，配好之后还得重新走一遍链路"""
    from core.utils.cache.manager import cache_manager, CacheType

    await weather_module.get_weather(
        FakeConn({"get_weather": {"api_host": "h"}}), location="没配密钥市"
    )

    assert cache_manager.get(CacheType.WEATHER, "failed_weather_没配密钥市_zh_CN") is None


async def test_no_credential_leaves_the_request_out(monkeypatch):
    """没配凭据就别去撞接口，调用次数得是零"""
    called = []

    async def fake_city_info(*args, **kwargs):
        called.append(1)
        return None

    monkeypatch.setattr(weather_module, "fetch_city_info", fake_city_info)

    await weather_module.get_weather(FakeConn(), location="无凭据市")

    assert called == []


# ---------------------------------------------------------------------------
# 网页解析
# ---------------------------------------------------------------------------


def test_parse_weather_info_returns_none_when_city_name_missing():
    """页面结构变了要返回 None，抛异常的话 Python 原文会被念给用户"""
    soup = BeautifulSoup("<html><div>没有城市名</div></html>", "html.parser")

    assert weather_module.parse_weather_info(soup) is None


def test_parse_weather_info_returns_none_when_forecast_icon_missing():
    html = """
    <h1 class="c-submenu__location">杭州市</h1>
    <div class="city-forecast-tabs__row">
      <div class="date-bg"><span class="date">今天10月24日</span></div>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")

    assert weather_module.parse_weather_info(soup) is None


def test_parse_weather_info_returns_none_when_soup_is_missing():
    assert weather_module.parse_weather_info(None) is None


async def test_broken_web_page_gives_a_neutral_message(monkeypatch):
    async def fake_city_info(*args, **kwargs):
        return {"id": "1", "name": "杭州", "fxLink": "https://example.com/x.html"}

    async def fake_weather_data(*args, **kwargs):
        return None

    async def fake_page(url):
        return BeautifulSoup("<html></html>", "html.parser")

    monkeypatch.setattr(weather_module, "fetch_city_info", fake_city_info)
    monkeypatch.setattr(weather_module, "fetch_weather_data", fake_weather_data)
    monkeypatch.setattr(weather_module, "fetch_weather_page", fake_page)

    response = await weather_module.get_weather(
        FakeConn({"get_weather": {"api_key": "k", "api_host": "h"}}), location="页面变了市"
    )

    assert response.result == "暂时查不到天气数据，请稍后再试"
    assert "AttributeError" not in str(response.result)
    assert "NoneType" not in str(response.result)


# ---------------------------------------------------------------------------
# 报告内容
# ---------------------------------------------------------------------------


def test_report_carries_the_observation_time():
    report = weather_module.build_weather_report(
        {"name": "杭州"},
        {"now": {"text": "多云", "obsTime": "2026-10-24T09:52+08:00"}},
        {"daily": []},
    )

    assert "观测时间：2026-10-24 09:52+08:00" in report


def test_report_falls_back_to_the_top_level_update_time():
    """没有观测时间的时候，顶层那个是数据更新时间，标签不能写成观测时间"""
    report = weather_module.build_weather_report(
        {"name": "杭州"},
        {"updateTime": "2026-10-24T10:00+08:00", "now": {"text": "多云"}},
        {"daily": []},
    )

    assert "数据更新时间：2026-10-24 10:00+08:00" in report
    assert "观测时间" not in report


def test_report_prefers_the_observation_time_over_the_update_time():
    report = weather_module.build_weather_report(
        {"name": "杭州"},
        {
            "updateTime": "2026-10-24T10:00+08:00",
            "now": {"text": "多云", "obsTime": "2026-10-24T09:52+08:00"},
        },
        {"daily": []},
    )

    assert "观测时间：2026-10-24 09:52+08:00" in report
    assert "数据更新时间" not in report


def test_report_without_any_time_has_no_empty_line():
    report = weather_module.build_weather_report(
        {"name": "杭州"}, {"now": {"text": "多云"}}, {"daily": []}
    )

    assert "观测时间" not in report
    assert "数据更新时间" not in report


# ---------------------------------------------------------------------------
# 日期按北京时间
# ---------------------------------------------------------------------------

# 时间停在 UTC 的 10 月 23 日晚上 16:30，北京时间已经是 24 号了
FROZEN_UTC = datetime.datetime(2026, 10, 23, 16, 30, tzinfo=datetime.timezone.utc)


class FrozenDatetime(datetime.datetime):
    @classmethod
    def now(cls, tz=None):
        return FROZEN_UTC.astimezone(tz) if tz else FROZEN_UTC


class FrozenDate(datetime.date):
    """服务器本地时区是 UTC，这个时刻服务器那边还是 23 号"""

    @classmethod
    def today(cls):
        return cls(2026, 10, 23)


class FrozenDatetimeModule:
    datetime = FrozenDatetime
    date = FrozenDate
    timezone = _timezone
    timedelta = _timedelta


def test_today_follows_beijing_time_not_the_server_clock(monkeypatch):
    """服务器时区是 UTC 时，「今天」得按北京时间算，否则凌晨八点前会说错一整天"""
    original_tz = os.environ.get("TZ")
    os.environ["TZ"] = "UTC"
    time.tzset()
    try:
        monkeypatch.setattr(weather_module, "datetime", FrozenDatetimeModule)

        assert FROZEN_UTC.astimezone().date() == datetime.date(2026, 10, 23), "服务器本地还是 23 号"
        assert weather_module.beijing_today() == datetime.date(2026, 10, 24)
        assert (
            weather_module.format_forecast_date("2026-10-24") == "今天10月24日"
        ), "北京已经跨天了，「今天」还停在 23 号"
        assert weather_module.format_forecast_date("2026-10-25") == "明天10月25日"
    finally:
        if original_tz is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = original_tz
        time.tzset()



# ---------------------------------------------------------------------------
# 两条路径的写法
# ---------------------------------------------------------------------------


def test_forecast_date_writing_is_the_same_on_both_paths():
    today = datetime.date(2026, 10, 24)

    assert weather_module.format_forecast_date("2026-10-24", today) == "今天10月24日"
    assert weather_module.format_forecast_date("今天10月24日", today) == "今天10月24日"
    assert weather_module.format_forecast_date("2026-10-25", today) == "明天10月25日"
    assert weather_module.format_forecast_date("周日10月25日", today) == "明天10月25日"
    assert weather_module.format_forecast_date("2026-10-27", today) == "周二10月27日"
    assert weather_module.format_forecast_date("周二10月27日", today) == "周二10月27日"


def test_both_paths_write_the_same_date_and_units():
    today = _today()
    iso_date = today.isoformat()
    web_date = f"今天{today.month}月{today.day}日"

    json_report = weather_module.build_weather_report(
        {"name": "杭州市"},
        {
            "now": {
                "text": "多云",
                "temp": "13",
                "feelsLike": "13",
                "humidity": "97",
                "windDir": "西北风",
                "windScale": "4",
                "vis": "9",
                "pressure": "1009",
                "precip": "0.0",
            }
        },
        {
            "daily": [
                {
                    "fxDate": iso_date,
                    "textDay": "中雨",
                    "iconDay": "306",
                    "tempMax": "13",
                    "tempMin": "9",
                }
            ]
        },
    )

    parsed = weather_module.parse_weather_info(
        BeautifulSoup(_web_page(web_date), "html.parser")
    )
    web_report = weather_module.format_weather_report(*parsed)

    for report in (json_report, web_report):
        assert f"{web_date}" in report
        assert "气温 9~13℃" in report
        assert "能见度: 9公里" in report
        assert "气压: 1009百帕" in report
        assert "降水量: 0.0毫米" in report
        assert "湿度: 97%" in report
        assert "体感温度: 13℃" in report
        assert "风力: 4级" in report


def test_web_page_units_are_written_in_chinese():
    parsed = weather_module.parse_weather_info(
        BeautifulSoup(_web_page("今天10月24日"), "html.parser")
    )

    _, _, current_basic, _, _ = parsed
    assert current_basic["能见度"] == "9公里"
    assert current_basic["气压"] == "1009百帕"
    assert current_basic["降水量"] == "0.0毫米"
    assert current_basic["湿度"] == "97%"
    assert current_basic["体感温度"] == "13℃"
    assert current_basic["风向"] == "西北风"
    assert current_basic["风力"] == "4级"


def test_web_page_temperature_uses_the_same_unit_as_the_api_path():
    parsed = weather_module.parse_weather_info(
        BeautifulSoup(_web_page("今天10月24日"), "html.parser")
    )

    _, _, _, temps_list, _ = parsed
    assert temps_list[0][2] == "13"
    assert temps_list[0][3] == "9"


def test_web_page_carries_the_observation_time():
    """网页这条路也得有观测时间，两条路径的报告才对得齐"""
    parsed = weather_module.parse_weather_info(
        BeautifulSoup(
            _web_page("今天10月24日", current_time="10月24日 09:52"), "html.parser"
        )
    )

    assert parsed[4] == "10月24日 09:52"
    assert "观测时间：10月24日 09:52" in weather_module.format_weather_report(*parsed)


def test_web_page_without_a_time_element_is_not_an_error():
    """页面结构变了取不到时间，就当作没有，不能抛异常"""
    parsed = weather_module.parse_weather_info(
        BeautifulSoup(_web_page("今天10月24日"), "html.parser")
    )

    assert parsed[4] is None
    assert "观测时间" not in weather_module.format_weather_report(*parsed)


# ---------------------------------------------------------------------------
# 等待时间
# ---------------------------------------------------------------------------


async def test_web_fallback_does_not_wait_long(fake_http):
    """网页只是兜底，等太久不值得"""
    fake_http.responder = lambda url, params: FakeResponse(text="<html></html>")

    await weather_module.fetch_weather_page("https://example.com/x.html")

    assert fake_http.init_kwargs["timeout"].read == 5.0


async def test_failure_is_remembered_so_the_next_ask_does_not_wait(monkeypatch):
    """上游挂着的时候别每次都把整条链路重走一遍"""
    calls = []

    async def fake_city_info(*args, **kwargs):
        calls.append(1)
        return None

    monkeypatch.setattr(weather_module, "fetch_city_info", fake_city_info)
    conn = FakeConn({"get_weather": {"api_key": "k", "api_host": "h"}})

    first = await weather_module.get_weather(conn, location="失败标记市")
    second = await weather_module.get_weather(conn, location="失败标记市")

    assert calls == [1]
    assert first.result == second.result
