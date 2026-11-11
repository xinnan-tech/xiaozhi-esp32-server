"""Tests for the Outcrawl source of the web_search plugin.

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

    async def post(self, url, json=None, headers=None):
        FakeAsyncClient.requests.append({"url": url, "json": json, "headers": headers})
        return FakeAsyncClient.response


@pytest.fixture
def fake_http(monkeypatch):
    """Replace httpx.AsyncClient with the recording fake."""
    FakeAsyncClient.requests = []
    FakeAsyncClient.response = FakeResponse(payload={"hits": []})
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    return FakeAsyncClient


class FakeConn:
    def __init__(self, web_search_config):
        self.config = {"plugins": {"web_search": web_search_config}}


async def test_outcrawl_sends_bearer_key_and_limit(fake_http):
    await web_search_module._search_outcrawl("oc-key", "上海天气", 5)

    [request] = fake_http.requests
    assert request["url"] == "https://api.outcrawl.ai/v1/search"
    assert request["json"] == {"query": "上海天气", "limit": 5}
    assert request["headers"]["Authorization"] == "Bearer oc-key"
    assert request["headers"]["User-Agent"] == "xiaozhi-esp32-server"


@pytest.mark.parametrize(("max_results", "limit"), [(0, 1), (50, 20)])
async def test_outcrawl_clamps_limit(fake_http, max_results, limit):
    await web_search_module._search_outcrawl("oc-key", "q", max_results)

    assert fake_http.requests[0]["json"]["limit"] == limit


async def test_outcrawl_formats_titles_and_snippets_without_urls(fake_http):
    fake_http.response = FakeResponse(
        payload={
            "hits": [
                {"url": "https://a.example/1", "title": "标题一", "snippet": "摘要一", "rank": 1},
                {"url": "https://a.example/2", "title": None, "snippet": "", "rank": 2},
                {"url": "https://a.example/3", "title": "标题三", "snippet": "摘要三", "rank": 3},
            ],
            "usage": {"credits": "1.5"},
        }
    )

    result = await web_search_module._search_outcrawl("oc-key", "q", 2)

    assert result == "【联网搜索结果】\n1. 标题：标题一\n   摘要：摘要一\n2. 标题：无标题"
    assert "https://" not in result


async def test_outcrawl_empty_hits(fake_http):
    fake_http.response = FakeResponse(payload={"hits": []})

    assert await web_search_module._search_outcrawl("oc-key", "q", 3) == "未找到相关搜索结果。"


@pytest.mark.parametrize(
    ("code", "message"),
    [
        ("unauthorized", "联网搜索请求失败，请检查API Key是否正确。"),
        ("quota_exceeded", "联网搜索被限流或额度已用完，请稍后重试或检查Outcrawl账户余额。"),
        ("bad_request", "联网搜索请求失败，请稍后重试。"),
        ("internal", "联网搜索请求失败，请稍后重试。"),
    ],
)
async def test_outcrawl_error_code(fake_http, code, message):
    fake_http.response = FakeResponse(
        status_code=429, payload={"code": code, "message": "denied", "details": {}}
    )

    assert await web_search_module._search_outcrawl("oc-key", "q", 3) == message


async def test_web_search_dispatches_to_outcrawl(fake_http):
    fake_http.response = FakeResponse(payload={"hits": [{"url": "https://a.example", "title": "T", "snippet": "S"}]})
    conn = FakeConn({"provider": "Outcrawl", "api_key": "oc-key", "max_results": 3})

    response = await web_search_module.web_search(conn, "q")

    assert response.action == Action.REQLLM
    assert response.result == "【联网搜索结果】\n1. 标题：T\n   摘要：S"
    assert fake_http.requests[0]["json"] == {"query": "q", "limit": 3}
