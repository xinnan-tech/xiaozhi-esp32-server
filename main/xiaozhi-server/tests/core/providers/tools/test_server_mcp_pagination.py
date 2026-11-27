"""服务端 MCP 初始化必须读取 tools/list 的全部分页。"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from unittest.mock import Mock

import anyio
import pytest
from mcp import ClientSession
from mcp.types import ListToolsResult, Tool

from core.providers.tools.server_mcp import mcp_client


def _page(names, cursor=None):
    return ListToolsResult(
        tools=[Tool(name=name, description=name,
                    input_schema={"type": "object", "properties": {}})
               for name in names],
        next_cursor=cursor,
    )


def _session_fixture(monkeypatch, pages):
    requests = []

    class Session(ClientSession):
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            pass

        async def initialize(self):
            pass

        async def send_request(self, request, response_type, **_kwargs):
            cursor = request.params.cursor if request.params else None
            requests.append(cursor)
            result = pages[cursor]
            if isinstance(result, Exception):
                raise result
            return result

    @asynccontextmanager
    async def transport(_params):
        send, receive = anyio.create_memory_object_stream(10)
        async with send, receive:
            yield receive, send

    monkeypatch.setattr(mcp_client, "ClientSession", Session)
    monkeypatch.setattr(mcp_client, "stdio_client", transport)
    monkeypatch.setattr(mcp_client, "setup_logging", Mock())
    return requests


@pytest.mark.parametrize("pages,expected_cursors,expected_names", [
    ({None: _page(["first", "last.tool"])},
     [None], ["first", "last_tool"]),
    ({None: _page(["first"], "page2"),
      "page2": _page(["last.tool"])},
     [None, "page2"], ["first", "last_tool"]),
    ({None: _page(["first"], "page2"),
      "page2": _page([], "page3"),
      "page3": _page(["last.tool"])},
     [None, "page2", "page3"], ["first", "last_tool"]),
    ({None: _page([], ""), "": _page(["last.tool"])},
     [None, ""], ["last_tool"]),
    ({None: _page([])}, [None], []),
])
def test_initialization_registers_all_pages(
    monkeypatch, pages, expected_cursors, expected_names
):
    requests = _session_fixture(monkeypatch, pages)

    async def run():
        client = mcp_client.ServerMCPClient({"command": "fixture"})
        try:
            await asyncio.wait_for(client.initialize(), timeout=2)
            if client._worker_task.done():
                raise client._worker_task.exception()
            assert client.is_connected()
            assert requests == expected_cursors
            assert list(client.tools_dict) == expected_names
            assert [tool["function"]["name"]
                    for tool in client.get_available_tools()] == expected_names
            if "last_tool" in expected_names:
                assert client.name_mapping["last_tool"] == "last.tool"
        finally:
            await client.cleanup()

    asyncio.run(run())


@pytest.mark.parametrize("pages,error", [
    ({None: _page(["first"], "page2"),
      "page2": RuntimeError("page unavailable")}, RuntimeError),
    ({None: _page(["first"], "page2"),
      "page2": _page([], "page2")}, ValueError),
])
def test_invalid_page_does_not_register_a_partial_tool_list(
    monkeypatch, pages, error
):
    _session_fixture(monkeypatch, pages)

    async def run():
        client = mcp_client.ServerMCPClient({"command": "fixture"})
        try:
            await asyncio.wait_for(client.initialize(), timeout=2)
            assert client._worker_task.done()
            with pytest.raises(error):
                await client._worker_task
            assert not client.is_connected()
            assert client.get_available_tools() == []
        finally:
            await client.cleanup()

    asyncio.run(run())
