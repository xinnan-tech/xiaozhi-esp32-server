from typing import Any

from .base import Plugin


class PluginManager:
    def __init__(self) -> None:
        self._plugins: list[Plugin] = []
        self._by_name: dict[str, Plugin] = {}

    def register(self, *plugins: Plugin) -> None:
        for plugin in sorted(plugins, key=lambda item: getattr(item, "priority", 50)):
            if plugin in self._plugins:
                continue
            self._plugins.append(plugin)
            name = getattr(plugin, "name", "")
            if isinstance(name, str) and name:
                self._by_name[name] = plugin

    def get_plugin(self, name: str) -> Plugin | None:
        return self._by_name.get(name)

    def setup_all(self, app: Any) -> None:
        for plugin in list(self._plugins):
            plugin.setup(app)

    def start_all(self) -> None:
        for plugin in list(self._plugins):
            plugin.start()

    def stop_all(self) -> None:
        for plugin in reversed(self._plugins):
            plugin.stop()

    def shutdown_all(self) -> None:
        for plugin in reversed(self._plugins):
            plugin.shutdown()
