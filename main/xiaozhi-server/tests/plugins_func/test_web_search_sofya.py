"""Tests for the Sofya source of the web_search plugin.

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
    FakeAsyncClient.response = FakeResponse(payload={"results": []})
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    return FakeAsyncClient


class FakeConn:
    def __init__(self, web_search_config):
        self.config = {"plugins": {"web_search": web_search_config}}


async def test_sofya_sends_bearer_key_and_snippets_depth(fake_http):
    await web_search_module._search_sofya("sofya_live_key", "上海天气", 5)

    [request] = fake_http.requests
    assert request["url"] == "https://sofya.co/v1/search"
    assert request["json"] == {"query": "上海天气", "max_results": 5, "search_depth": "snippets"}
    assert request["headers"]["Authorization"] == "Bearer sofya_live_key"
    assert request["headers"]["User-Agent"] == "xiaozhi-esp32-server"


@pytest.mark.parametrize(("max_results", "sent"), [(0, 1), (50, 20)])
async def test_sofya_clamps_max_results(fake_http, max_results, sent):
    await web_search_module._search_sofya("sofya_live_key", "q", max_results)

    assert fake_http.requests[0]["json"]["max_results"] == sent


async def test_sofya_formats_titles_dates_and_snippets_without_urls(fake_http):
    fake_http.response = FakeResponse(
        payload={
            "query": "q",
            "answer": None,
            "results": [
                {
                    "url": "https://a.example/1",
                    "title": "标题一",
                    "content": "摘要一",
                    "description": "摘要一",
                    "fetched": False,
                    "published_date": "2026-11-10",
                },
                {"url": "https://a.example/2", "title": "", "content": "", "description": None, "published_date": None},
                {"url": "https://a.example/3", "title": "标题三", "content": "摘要三"},
            ],
            "search_depth": "snippets",
            "credits_used": 1,
        }
    )

    result = await web_search_module._search_sofya("sofya_live_key", "q", 2)

    assert result == "【联网搜索结果】\n1. 标题：标题一\n   日期：2026-11-10\n   摘要：摘要一\n2. 标题：无标题"
    assert "https://" not in result


async def test_sofya_falls_back_to_content_when_description_is_missing(fake_http):
    fake_http.response = FakeResponse(
        payload={"results": [{"url": "https://a.example", "title": "T", "content": "C", "description": None}]}
    )

    assert await web_search_module._search_sofya("sofya_live_key", "q", 3) == "【联网搜索结果】\n1. 标题：T\n   摘要：C"


async def test_sofya_empty_results(fake_http):
    fake_http.response = FakeResponse(payload={"results": []})

    assert await web_search_module._search_sofya("sofya_live_key", "q", 3) == "未找到相关搜索结果。"


@pytest.mark.parametrize(
    ("status", "code", "message"),
    [
        (401, "unauthorized", "联网搜索请求失败，请检查API Key是否正确。"),
        (402, "insufficient_credits", "联网搜索额度已用完，请检查Sofya账户余额。"),
        (402, "key_cap_reached", "联网搜索额度已用完，请检查Sofya账户余额。"),
        (429, "rate_limited", "联网搜索请求失败，请稍后重试。"),
        (503, "search_unavailable", "联网搜索请求失败，请稍后重试。"),
    ],
)
async def test_sofya_error_status(fake_http, status, code, message):
    fake_http.response = FakeResponse(status_code=status, payload={"error": code, "detail": "denied"})

    assert await web_search_module._search_sofya("sofya_live_key", "q", 3) == message


async def test_web_search_dispatches_to_sofya(fake_http):
    fake_http.response = FakeResponse(
        payload={"results": [{"url": "https://a.example", "title": "T", "description": "S", "content": "S"}]}
    )
    conn = FakeConn({"provider": "Sofya", "api_key": "sofya_live_key", "max_results": 3})

    response = await web_search_module.web_search(conn, "q")

    assert response.action == Action.REQLLM
    assert response.result == "【联网搜索结果】\n1. 标题：T\n   摘要：S"
    assert fake_http.requests[0]["json"] == {"query": "q", "max_results": 3, "search_depth": "snippets"}
