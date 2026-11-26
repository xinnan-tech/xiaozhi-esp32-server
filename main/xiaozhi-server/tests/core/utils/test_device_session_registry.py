import asyncio

from core.utils.device_session_registry import DeviceSessionRegistry


class FakeHandler:
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f"FakeHandler({self.name})"


def test_same_device_rebind_returns_old_handler():
    async def run():
        reg = DeviceSessionRegistry()
        first, second = FakeHandler("first"), FakeHandler("second")
        assert await reg.bind("dev-1", first) is None
        assert await reg.bind("dev-1", second) is first
        assert reg.get("dev-1") is second
        assert reg.active_count() == 1

    asyncio.run(run())


def test_bind_without_device_id_is_noop():
    async def run():
        reg = DeviceSessionRegistry()
        handler = FakeHandler("h")
        assert await reg.bind(None, handler) is None
        assert await reg.bind("", handler) is None
        assert reg.active_count() == 0

    asyncio.run(run())


def test_rebind_same_handler_returns_none():
    async def run():
        reg = DeviceSessionRegistry()
        handler = FakeHandler("h")
        await reg.bind("dev-1", handler)
        assert await reg.bind("dev-1", handler) is None
        assert reg.get("dev-1") is handler

    asyncio.run(run())


def test_release_only_removes_own_handler():
    async def run():
        reg = DeviceSessionRegistry()
        old, new = FakeHandler("old"), FakeHandler("new")
        await reg.bind("dev-1", old)
        await reg.bind("dev-1", new)
        # 旧会话收尾时不得把新会话从注册表里删掉
        assert await reg.release("dev-1", old) is False
        assert reg.get("dev-1") is new
        assert await reg.release("dev-1", new) is True
        assert reg.get("dev-1") is None
        assert reg.active_count() == 0

    asyncio.run(run())


def test_devices_are_isolated():
    async def run():
        reg = DeviceSessionRegistry()
        a, b = FakeHandler("a"), FakeHandler("b")
        await reg.bind("dev-a", a)
        await reg.bind("dev-b", b)
        assert reg.active_count() == 2
        assert reg.get("dev-a") is a and reg.get("dev-b") is b

    asyncio.run(run())
