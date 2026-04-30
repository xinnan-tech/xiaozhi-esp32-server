import logging
from typing import Any

from ..core import MicrophoneListener
from .base import Plugin

logger = logging.getLogger(__name__)


class AudioPlugin(Plugin):
    name = "audio"
    priority = 10

    def __init__(self) -> None:
        self.app = None
        self.source: MicrophoneListener | None = None

    def setup(self, app: Any) -> None:
        self.app = app
        self.source = MicrophoneListener(app.config)
        self.app.audio_source = self.source

    def start(self) -> None:
        if self.source is None:
            logger.warning("audio source not initialized")
            return
        self.source.start()

    def stop(self) -> None:
        if self.source is not None:
            self.source.stop()

    def shutdown(self) -> None:
        if self.app is not None:
            self.app.audio_source = None
        self.source = None
        self.app = None
