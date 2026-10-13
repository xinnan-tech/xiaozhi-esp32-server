"""Offline reproduction: no real devices, credentials, HTTP server or model APIs.

Usage: python -B tests/reproduce_manage_api_client_retention.py path/to/config/manage_api_client.py
Keeps CLOSED loop objects alive to avoid Python reusing their integer IDs.
This makes the cache-lifetime check deterministic; it is not an RSS benchmark.

依赖真实 httpx.AsyncClient + MockTransport，不进 pytest 套件
（tests/conftest.py 的 mock 层会全局替换 AsyncClient）。
"""
__test__ = False

import asyncio
import gc
import importlib.util
import json
import sys
import weakref
from unittest.mock import patch

import httpx


def main():
    spec = importlib.util.spec_from_file_location("client_under_test", sys.argv[1])
    api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api)
    cls = api.ManageApiClient
    cls({"manager-api": {"url": "http://offline.invalid/xiaozhi",
                        "secret": "synthetic-test", "max_retries": 0}})
    real_client = httpx.AsyncClient
    refs, loops = [], []

    def factory(**kwargs):
        transport = httpx.MockTransport(
            lambda request: httpx.Response(200, json={"code": 0, "data": True})
        )
        client = real_client(transport=transport, **kwargs)
        refs.append(weakref.ref(client))
        return client

    try:
        with patch.object(api.httpx, "AsyncClient", side_effect=factory):
            for _ in range(100):
                loop = asyncio.new_event_loop()
                loops.append(loop)
                try:
                    assert loop.run_until_complete(
                        cls._execute_async_request("POST", "/synthetic-report")
                    ) is True
                finally:
                    loop.close()
        gc.collect()
        retained = [ref() for ref in refs if ref() is not None]
        print(json.dumps({
            "requests_completed": 100,
            "all_loops_closed": all(loop.is_closed() for loop in loops),
            "cached_clients_after_gc": len(getattr(cls, "_async_clients", {})),
            "live_clients_after_gc": len(retained),
            "unclosed_clients_after_gc": sum(not client.is_closed for client in retained),
        }, sort_keys=True))
    finally:
        cls.safe_close()
        loops.clear()


if __name__ == "__main__":
    main()
