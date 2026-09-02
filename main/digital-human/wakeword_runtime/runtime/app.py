import logging
from typing import Protocol

from ..config import RuntimeConfig
from ..plugins import AudioPlugin, PluginManager, WakeWordPlugin

logger = logging.getLogger(__name__)


class EventPublisher(Protocol):
    def publish_service_ready(self) -> None:
        ...

    def publish_service_stopping(self) -> None:
        ...

    def publish_detected(self, wake_word: str) -> None:
        ...


class TestRuntimeApplication:
    def __init__(self, config: RuntimeConfig, event_publisher: EventPublisher) -> None:
        self.config = config
        self.event_bridge = event_publisher
        self.plugins = PluginManager()
        self.audio_source = None
        self._is_setup = False
        self._is_running = False

    def setup(self) -> None:
        if self._is_setup:
            return

        if self.config.wakeword_enabled:
            self.plugins.register(
                AudioPlugin(),
                WakeWordPlugin(),
            )
        self.plugins.setup_all(self)
        self._is_setup = True

    def start(self) -> None:
        if self._is_running:
            return

        self.setup()
        self.plugins.start_all()
        if self.config.wakeword_enabled:
            self.event_bridge.publish_service_ready()
        self._is_running = True
        logger.info("test runtime application started")

    def stop(self) -> None:
        if not self._is_running:
            return

        self.event_bridge.publish_service_stopping()
        self.plugins.stop_all()
        self._is_running = False
        logger.info("test runtime application stopped")

    def shutdown(self) -> None:
        self.stop()
        if self._is_setup:
            self.plugins.shutdown_all()

    def handle_wake_word_detected(self, wake_word: str, full_text: str) -> None:
        _ = full_text
        logger.info("wake word detected: %s", wake_word)
        self.event_bridge.publish_detected(wake_word)
