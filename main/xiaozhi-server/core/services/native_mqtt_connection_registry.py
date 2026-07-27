import asyncio
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional


@dataclass(frozen=True)
class NativeMqttConnection:
    client_id: str
    device_id: Optional[str]
    connection_id: int
    context: Any
    transport: Any

    @property
    def is_alive(self) -> bool:
        return bool(getattr(self.transport, "is_connected", False))


class NativeMqttConnectionRegistry:
    def __init__(self):
        self._connections: Dict[str, NativeMqttConnection] = {}
        self._devices: Dict[str, NativeMqttConnection] = {}
        self._lock = asyncio.Lock()

    async def register(self, context: Any, transport: Any) -> bool:
        client_id = getattr(transport, "client_id", None)
        raw_connection = getattr(transport, "raw_connection", None)
        connection_id = getattr(raw_connection, "connection_id", None)
        if not client_id or connection_id is None:
            return False

        entry = NativeMqttConnection(
            client_id=client_id,
            device_id=self._normalize_device_id(
                getattr(context, "device_id", None)
            ),
            connection_id=connection_id,
            context=context,
            transport=transport,
        )
        async with self._lock:
            previous_client = self._connections.get(client_id)
            previous_device = (
                self._devices.get(entry.device_id)
                if entry.device_id
                else None
            )
            for previous in (previous_client, previous_device):
                if previous is None or previous is entry:
                    continue
                if self._connections.get(previous.client_id) is previous:
                    self._connections.pop(previous.client_id, None)
                if (
                    previous.device_id
                    and self._devices.get(previous.device_id) is previous
                ):
                    self._devices.pop(previous.device_id, None)
            self._connections[client_id] = entry
            if entry.device_id:
                self._devices[entry.device_id] = entry
        return True

    async def unregister(self, context: Any, transport: Any) -> bool:
        client_id = getattr(transport, "client_id", None)
        if not client_id:
            return False

        async with self._lock:
            entry = self._connections.get(client_id)
            if (
                entry is None
                or entry.context is not context
                or entry.transport is not transport
            ):
                return False
            self._connections.pop(client_id, None)
            if (
                entry.device_id
                and self._devices.get(entry.device_id) is entry
            ):
                self._devices.pop(entry.device_id, None)
        return True

    async def resolve(self, client_id: str) -> Optional[NativeMqttConnection]:
        async with self._lock:
            entry = self._connections.get(client_id)
            if entry is None or not entry.is_alive:
                return None
            return entry

    async def status(self, client_ids: Iterable[str]) -> Dict[str, Dict[str, Any]]:
        async with self._lock:
            result = {}
            for client_id in client_ids:
                entry = self._connections.get(client_id)
                exists = entry is not None
                result[client_id] = {
                    "isAlive": bool(entry and entry.is_alive),
                    "exists": exists,
                    "backend": "native",
                }
        return result

    async def resolve_device(
        self, device_id: str
    ) -> Optional[NativeMqttConnection]:
        async with self._lock:
            return self.resolve_device_now(device_id)

    def resolve_device_now(
        self, device_id: str
    ) -> Optional[NativeMqttConnection]:
        normalized = self._normalize_device_id(device_id)
        entry = self._devices.get(normalized) if normalized else None
        if entry is None or not entry.is_alive:
            return None
        return entry

    async def clear(self) -> None:
        async with self._lock:
            self._connections.clear()
            self._devices.clear()

    async def size(self) -> int:
        async with self._lock:
            return len(self._connections)

    @property
    def count(self) -> int:
        return len(self._connections)

    @staticmethod
    def _normalize_device_id(device_id: Optional[str]) -> Optional[str]:
        if not isinstance(device_id, str):
            return None
        normalized = device_id.strip().lower().replace("-", ":")
        return normalized or None
