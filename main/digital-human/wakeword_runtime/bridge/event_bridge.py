import json
import logging
import queue
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)


class WakewordEventBridge:
    def __init__(self) -> None:
        self._clients: list[queue.Queue[str]] = []
        self._clients_lock = threading.Lock()
        self._running = True

    @property
    def is_running(self) -> bool:
        return self._running

    def build_ready_message(self) -> str:
        return self.build_message(
            "bridge_connected",
            {"status": "ready"},
        )

    def publish_detected(self, wake_word: str) -> None:
        self.publish(
            "wake_word_detected",
            {
                "wake_word": wake_word,
                "timestamp": time.time(),
            },
        )

    def publish(self, event_type: str, payload: dict[str, Any] | None = None) -> None:
        if not self._running:
            return

        message = self.build_message(event_type, payload or {})
        with self._clients_lock:
            clients = list(self._clients)

        stale_clients: list[queue.Queue[str]] = []
        for client_queue in clients:
            try:
                client_queue.put_nowait(message)
            except queue.Full:
                stale_clients.append(client_queue)

        if stale_clients:
            with self._clients_lock:
                for client_queue in stale_clients:
                    if client_queue in self._clients:
                        self._clients.remove(client_queue)

    def add_client(self) -> queue.Queue[str]:
        client_queue: queue.Queue[str] = queue.Queue(maxsize=16)
        with self._clients_lock:
            self._clients.append(client_queue)
        return client_queue

    def build_message(
        self,
        event_type: str,
        payload: dict[str, Any] | None = None,
        request_id: str | None = None,
        success: bool = True,
        error: str | None = None,
    ) -> str:
        message: dict[str, Any] = {
            "type": event_type,
            "requestId": request_id,
            "success": success,
            "payload": payload or {},
        }
        if error:
            message["error"] = error
        return json.dumps(message, ensure_ascii=False)

    def remove_client(self, client_queue: queue.Queue[str]) -> None:
        with self._clients_lock:
            if client_queue in self._clients:
                self._clients.remove(client_queue)

    def publish_service_ready(self) -> None:
        self.publish("service_ready", {"status": "ready"})

    def publish_service_stopping(self) -> None:
        self.publish("service_stopping", {"status": "stopping"})

    def close(self) -> None:
        if not self._running:
            return

        self.publish_service_stopping()
        self._running = False
        with self._clients_lock:
            clients = list(self._clients)
            self._clients.clear()

        for client_queue in clients:
            try:
                client_queue.put_nowait("__bridge_closed__")
            except queue.Full:
                pass
