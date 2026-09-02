import logging
from typing import Any

from ..core import WakewordDetector
from .base import Plugin

logger = logging.getLogger(__name__)


class WakeWordPlugin(Plugin):
    name = "wake_word"
    priority = 30

    def __init__(self) -> None:
        self.app = None
        self.detector: WakewordDetector | None = None

    def setup(self, app: Any) -> None:
        self.app = app
        self.detector = WakewordDetector(app.config)
        if not self.detector.enabled:
            self.detector = None
            return
        self.detector.on_detected(self._on_detected)
        self.detector.on_error = self._on_error

    def start(self) -> None:
        if self.detector is None:
            return

        audio_plugin = self.app.plugins.get_plugin("audio") if self.app else None
        audio_source = getattr(audio_plugin, "source", None)
        if audio_source is None:
            logger.warning("audio source unavailable, wakeword plugin not started")
            return

        self.detector.start(audio_source)

    def stop(self) -> None:
        if self.detector is not None:
            self.detector.stop()

    def shutdown(self) -> None:
        self.detector = None
        self.app = None

    def _on_detected(self, wake_word: str, full_text: str) -> None:
        if self.app is None:
            return
        self.app.handle_wake_word_detected(wake_word, full_text)

    def _on_error(self, error: Exception) -> None:
        logger.error("wakeword detection error: %s", error)
