import asyncio
import unittest

from core.connection_initialization import (
    DEFAULT_BIND_STATUS_TIMEOUT_SECONDS,
    bind_status_timeout_seconds,
    wait_for_bind_status,
)


class ConnectionInitializationTest(unittest.IsolatedAsyncioTestCase):
    async def test_waits_for_status_beyond_legacy_one_second_gate(self):
        event = asyncio.Event()

        async def complete_later():
            await asyncio.sleep(1.05)
            event.set()

        task = asyncio.create_task(complete_later())
        try:
            ready = await wait_for_bind_status(event, {"server": {}})
        finally:
            await task

        self.assertTrue(ready)

    async def test_returns_false_when_bounded_wait_expires(self):
        event = asyncio.Event()

        ready = await wait_for_bind_status(
            event, {"server": {"bind_status_timeout_seconds": 0}}
        )

        self.assertFalse(ready)

    def test_timeout_uses_safe_default_and_bounds(self):
        self.assertEqual(
            bind_status_timeout_seconds({}), DEFAULT_BIND_STATUS_TIMEOUT_SECONDS
        )
        self.assertEqual(
            bind_status_timeout_seconds(
                {"server": {"bind_status_timeout_seconds": "invalid"}}
            ),
            DEFAULT_BIND_STATUS_TIMEOUT_SECONDS,
        )
        self.assertEqual(
            bind_status_timeout_seconds(
                {"server": {"bind_status_timeout_seconds": 999}}
            ),
            60.0,
        )


if __name__ == "__main__":
    unittest.main()
