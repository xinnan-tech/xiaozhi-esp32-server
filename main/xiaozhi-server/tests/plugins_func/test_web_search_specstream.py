"""Tests for the SpecStream source of the web_search plugin.

The HTTP layer is replaced with a fake client and every request is recorded.
Nothing here touches the network.
"""
import httpx
import pytest

from plugins_func.functions import web_search as web_search_module
from plugins_func.register import Action


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self.payload = payload

    def json(self):
        return self.payload


class FakeAsyncClient:
    """Stands in for httpx.AsyncClient and records what was requested."""

    requests = []
    response = None

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def get(self, url, params=None, headers=None):
        FakeAsyncClient.requests.append({"url": url, "params": params, "headers": headers})
        return FakeAsyncClient.response


@pytest.fixture
def fake_http(monkeypatch):
    """Replace httpx.AsyncClient with the recording fake."""
    FakeAsyncClient.requests = []
    FakeAsyncClient.response = FakeResponse(payload={"data": {"sources": []}})
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    return FakeAsyncClient


class FakeConn:
    def __init__(self, web_search_config):
        self.config = {"plugins": {"web_search": web_search_config}}


async def test_specstream_sends_bearer_key_and_num(fake_http):
    await web_search_module._search_specstream("ss-key", "上海天气", 5)

    [request] = fake_http.requests
    assert request["url"] == "https://api.specstream.ai/v1/web-search"
    assert request["params"] == {"q": "上海天气", "num": 5}
    assert request["headers"]["Authorization"] == "Bearer ss-key"
    assert request["headers"]["User-Agent"] == "xiaozhi-esp32-server"


@pytest.mark.parametrize(("max_results", "num"), [(0, 1), (50, 10)])
async def test_specstream_clamps_num(fake_http, max_results, num):
    await web_search_module._search_specstream("ss-key", "q", max_results)

    assert fake_http.requests[0]["params"]["num"] == num


async def test_specstream_formats_answer_titles_dates_and_snippets_without_urls(fake_http):
    fake_http.response = FakeResponse(
        payload={
            "data": {
                "answer": {"value": "多云", "page": "https://a.example/1"},
                "sources": [
                    {"url": "https://a.example/1", "title": "标题一", "snippet": "摘要一", "published": "2026-11-10"},
                    {"url": "https://a.example/2", "title": "", "snippet": "", "published": None},
                    {"url": "https://a.example/3", "title": "标题三", "snippet": "摘要三"},
                ],
                "price_usd": 0.005,
            }
        }
    )

    result = await web_search_module._search_specstream("ss-key", "q", 2)

    assert result == "【联网搜索结果】\n总结：多云\n1. 标题：标题一\n   日期：2026-11-10\n   摘要：摘要一\n2. 标题：无标题"
    assert "https://" not in result


async def test_specstream_empty_sources(fake_http):
    fake_http.response = FakeResponse(payload={"data": {"answer": None, "sources": []}})

    assert await web_search_module._search_specstream("ss-key", "q", 3) == "未找到相关搜索结果。"


@pytest.mark.parametrize(
    ("status", "code", "message"),
    [
        (401, "invalid_token", "联网搜索请求失败，请检查API Key是否正确。"),
        (401, "missing_api_key", "联网搜索请求失败，请检查API Key是否正确。"),
        (402, "insufficient_balance", "联网搜索额度已用完，请检查SpecStream账户余额。"),
        (429, "rate_limited", "联网搜索请求失败，请稍后重试。"),
        (503, "capacity", "联网搜索请求失败，请稍后重试。"),
    ],
)
async def test_specstream_error_code(fake_http, status, code, message):
    fake_http.response = FakeResponse(
        status_code=status, payload={"error": {"code": code, "message": "denied", "details": {}}}
    )

    assert await web_search_module._search_specstream("ss-key", "q", 3) == message


async def test_web_search_dispatches_to_specstream(fake_http):
    fake_http.response = FakeResponse(
        payload={"data": {"answer": None, "sources": [{"url": "https://a.example", "title": "T", "snippet": "S"}]}}
    )
    conn = FakeConn({"provider": "SpecStream", "api_key": "ss-key", "max_results": 3})

    response = await web_search_module.web_search(conn, "q")

    assert response.action == Action.REQLLM
    assert response.result == "【联网搜索结果】\n1. 标题：T\n   摘要：S"
    assert fake_http.requests[0]["params"] == {"q": "q", "num": 3}
