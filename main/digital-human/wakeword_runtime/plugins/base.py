from typing import Any


class Plugin:
    name: str = "plugin"
    priority: int = 50

    def setup(self, app: Any) -> None:
        return None

    def start(self) -> None:
        return None

    def stop(self) -> None:
        return None

    def shutdown(self) -> None:
        return None
