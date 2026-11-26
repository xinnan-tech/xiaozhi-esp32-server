import asyncio

from core.websocket_server import WebSocketServer
from core.utils.device_session_registry import DeviceSessionRegistry


class _Logger:
    def bind(self, **kwargs):
        return self

    def info(self, *args, **kwargs):
        pass

    warning = error = debug = info


class FakeHandler:
    def __init__(self, name="old"):
        self.session_id = name
        self.client_abort = False
        self.cleared = False
        self.closed = False
        self.websocket = object()

    def clear_queues(self):
        self.cleared = True

    async def close(self, ws=None):
        self.closed = True


def _server():
    srv = WebSocketServer.__new__(WebSocketServer)  # 跳过 __init__ 的组件初始化
    srv.logger = _Logger()
    srv.device_sessions = DeviceSessionRegistry()
    return srv


def test_stale_session_is_aborted_cleared_and_closed():
    srv = _server()
    old = FakeHandler("old")

    async def run():
        await srv._close_stale_session("dev-1", old)

    asyncio.run(run())
    assert old.client_abort is True
    assert old.cleared is True
    assert old.closed is True


def test_stale_session_close_error_is_swallowed():
    srv = _server()

    class Boom(FakeHandler):
        async def close(self, ws=None):
            raise RuntimeError("ws already gone")

    old = Boom("boom")

    async def run():
        await srv._close_stale_session("dev-1", old)

    asyncio.run(run())  # 不向上抛，新连接不受影响
    assert old.client_abort is True
