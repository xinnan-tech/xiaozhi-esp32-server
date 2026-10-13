"""ManageApiClient 生命周期回归测试：直接以 unittest 运行，不依赖应用/模型与网络。

不进 pytest 套件：tests/conftest.py 的 mock 层（import 时全局替换
asyncio.sleep 与 httpx.AsyncClient）与本文件的时序断言、MockTransport
注入互相破坏；__test__ = False 使 pytest 跳过收集，请直接用 unittest 运行。
Usage: python -B tests/test_manage_api_client_lifecycle.py -v
"""
__test__ = False

import asyncio
from concurrent.futures import ThreadPoolExecutor
import gc
import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch
import weakref

import httpx


class ManageApiClientLifecycleTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        source = Path(os.environ.get('CLIENT_UNDER_TEST', str(
            Path(__file__).resolve().parents[1] / 'config/manage_api_client.py')))
        spec = importlib.util.spec_from_file_location('_lifecycle_client', source)
        self.api = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.api)
        self.cls = self.api.ManageApiClient
        self.cls({'manager-api': {'url': 'http://offline.invalid/xiaozhi',
                  'secret': 'synthetic-test', 'max_retries': 1, 'retry_delay': 0}})
        self.clients = []
        self.requests = []
        self.real_client = httpx.AsyncClient

    def transport(self, handler):
        def factory(**kwargs):
            async def handle(request):
                self.requests.append(request)
                return await handler(request)
            client = self.real_client(transport=httpx.MockTransport(handle), **kwargs)
            self.clients.append(client)
            return client
        return patch.object(self.api.httpx, 'AsyncClient', side_effect=factory)

    async def asyncTearDown(self):
        try:
            self.assertTrue(all(c.is_closed for c in self.clients), 'client escaped its request')
        finally:
            for client in self.clients:
                if not client.is_closed:
                    await client.aclose()
            self.cls.safe_close()

    async def test_success_preserves_url_headers_and_payload(self):
        async def handle(request):
            self.assertEqual(str(request.url), 'http://offline.invalid/xiaozhi/report')
            self.assertEqual(request.headers['authorization'], 'Bearer synthetic-test')
            self.assertEqual(request.content, b'{"value":123}')
            return httpx.Response(200, json={'code': 0, 'data': {'ok': True}})
        with self.transport(handle):
            self.assertEqual(await self.cls._execute_async_request('POST', '/report',
                             json={'value': 123}), {'ok': True})

    async def test_retry_reuses_client_until_request_ends(self):
        """重试在同一个 client（池内同一 keep-alive 连接）上进行，
        整个业务请求结束后才关闭——client 生命周期与业务请求对齐，
        而不是与单次尝试对齐。"""
        async def handle(request):
            if len(self.requests) == 1:
                return httpx.Response(503)
            # 第二次尝试时第一个 client 仍在服务（未被提前关闭）
            self.assertFalse(self.clients[0].is_closed)
            return httpx.Response(200, json={'code': 0, 'data': True})
        with self.transport(handle):
            self.assertTrue(await self.cls._execute_async_request('POST', '/report'))
        self.assertEqual(len(self.clients), 1)
        self.assertTrue(self.clients[0].is_closed)

    async def test_timeout_exhaustion_reuses_client_until_request_ends(self):
        async def handle(request):
            raise httpx.ReadTimeout('synthetic timeout', request=request)
        with self.transport(handle), self.assertRaises(httpx.ReadTimeout):
            await self.cls._execute_async_request('POST', '/report')
        self.assertEqual(len(self.clients), 1)
        self.assertTrue(self.clients[0].is_closed)

    async def test_remote_protocol_error_without_response_triggers_retry(self):
        """stale keep-alive 场景：响应从未开始，重试安全。"""
        async def handle(request):
            if len(self.requests) == 1:
                raise httpx.RemoteProtocolError(
                    'Server disconnected without sending a response.',
                    request=request)
            return httpx.Response(200, json={'code': 0, 'data': True})
        with self.transport(handle):
            self.assertTrue(await self.cls._execute_async_request('POST', '/report'))
        self.assertEqual(len(self.requests), 2)

    async def test_remote_protocol_error_incomplete_body_not_retried(self):
        """响应中途截断：服务端很可能已处理完请求，重试非幂等 POST
        会重复提交，必须直接失败。"""
        async def handle(request):
            raise httpx.RemoteProtocolError(
                'Peer closed connection without sending complete message body '
                '(discarded 10 of 100 read bytes)', request=request)
        with self.transport(handle), self.assertRaises(httpx.RemoteProtocolError):
            await self.cls._execute_async_request('POST', '/report')
        self.assertEqual(len(self.requests), 1)

    async def test_nonretryable_http_error(self):
        async def handle(request):
            return httpx.Response(403)
        with self.transport(handle), self.assertRaises(httpx.HTTPStatusError):
            await self.cls._execute_async_request('POST', '/report')
        self.assertEqual(len(self.clients), 1)

    async def test_business_error_and_invalid_json_release_client(self):
        for response, error in [
            (httpx.Response(200, json={'code': 10041, 'msg': 'missing'}), self.api.DeviceNotFoundException),
            (httpx.Response(200, json={'code': 10042, 'msg': 'bind'}), self.api.DeviceBindException),
            (httpx.Response(200, content=b'not-json'), ValueError),
        ]:
            async def handle(request):
                return response
            with self.transport(handle), self.assertRaises(error):
                await self.cls._execute_async_request('POST', '/report')
            self.assertTrue(self.clients[-1].is_closed)
        self.assertEqual(len(self.clients), 3)

    async def test_cancellation_does_not_close_concurrent_request(self):
        entered = [asyncio.Event(), asyncio.Event()]
        release = asyncio.Event()
        async def handle(request):
            index = len(self.requests) - 1
            entered[index].set()
            await release.wait()
            return httpx.Response(200, json={'code': 0, 'data': True})
        with self.transport(handle):
            first = asyncio.create_task(self.cls._execute_async_request('POST', '/first'))
            await asyncio.wait_for(entered[0].wait(), 2)
            second = asyncio.create_task(self.cls._execute_async_request('POST', '/second'))
            await asyncio.wait_for(entered[1].wait(), 2)
            first.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await first
            self.assertTrue(self.clients[0].is_closed)
            self.assertFalse(self.clients[1].is_closed)
            release.set()
            self.assertTrue(await asyncio.wait_for(second, 2))

    async def test_shutdown_allows_inflight_cleanup_and_blocks_report_entry(self):
        async def handle(request):
            self.cls.safe_close()
            return httpx.Response(200, json={'code': 0, 'data': True})
        with self.transport(handle):
            self.assertTrue(await self.api.report('device', 'session', 1, 'text', None, 0))
            self.assertIsNone(await self.api.report('device', 'session', 1, 'later', None, 0))
            with self.assertRaisesRegex(Exception, '已关闭'):
                await self.cls._execute_async_request('POST', '/report')
        self.assertEqual(len(self.clients), 1)

    async def test_safe_close_interrupts_retry_backoff(self):
        """safe_close 打断重试等待：已开始的尝试跑完，不发起新尝试，
        以 ManageApiShutdownError 收尾（与重试耗尽的网络异常可区分）。"""
        async def handle(request):
            return httpx.Response(503)
        original_delay = self.cls.retry_delay
        self.cls.retry_delay = 5.0  # setUp 默认 0，观察不到打断
        try:
            with self.transport(handle):
                task = asyncio.create_task(
                    self.cls._execute_async_request('POST', '/report'))
                await asyncio.sleep(0.2)  # 进入重试等待
                self.cls.safe_close()
                with self.assertRaises(self.api.ManageApiShutdownError) as ctx:
                    await task
                self.assertIsInstance(ctx.exception.__cause__, httpx.HTTPStatusError)
            # 只有第一次尝试：重试等待被打断，未发起新尝试
            self.assertEqual(len(self.clients), 1)
            self.assertEqual(len(self.requests), 1)
        finally:
            self.cls.retry_delay = original_delay

    async def test_many_temporary_loops_leave_no_open_clients(self):
        async def handle(request):
            return httpx.Response(200, json={'code': 0, 'data': True})
        def report_once(_):
            return asyncio.run(self.cls._execute_async_request('POST', '/report'))
        with self.transport(handle), ThreadPoolExecutor(max_workers=5) as pool:
            results = list(pool.map(report_once, range(100)))
        self.assertTrue(all(results))
        self.assertEqual(len(self.clients), 100)
        self.assertTrue(all(c.is_closed for c in self.clients))
        # 缓存回归网：释放测试持有的强引用后 client 必须可被 GC 回收，
        # 任何类级缓存（id(loop) dict / WeakKeyDictionary）重引入都会让存活数 > 0
        refs = [weakref.ref(c) for c in self.clients]
        self.clients.clear()
        gc.collect()
        self.assertEqual(sum(ref() is not None for ref in refs), 0)


if __name__ == '__main__':
    unittest.main()
