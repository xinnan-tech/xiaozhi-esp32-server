import yaml
import os
from .base import BasePlugin, PluginAction


class PluginConfig:
    """插件配置类"""

    def __init__(self, name, enabled=True, priority=100, config=None):
        self.name = name
        self.enabled = enabled
        self.priority = priority
        self.config = config or {}


class PluginManager:
    """插件管理器 - 支持优先级、启用开关和三状态返回"""

    def __init__(self, config_path=None):
        self.plugins = []
        self.plugin_configs = {}
        self.config_path = config_path

        if config_path and os.path.exists(config_path):
            self._load_plugin_configs_from_main()

    def _load_plugin_configs_from_main(self):
        """从主配置加载动态拦截器配置"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            for name, cfg in config.get('dynamic_interceptors', {}).items():
                self.plugin_configs[name] = PluginConfig(
                    name=name,
                    enabled=cfg.get('enabled', True),
                    priority=cfg.get('priority', 100),
                    config=cfg
                )
        except Exception as e:
            print(f"加载插件配置失败: {e}")

    def register_plugin(self, plugin, config=None):
        """注册插件"""
        if not isinstance(plugin, BasePlugin):
            return

        plugin_name = plugin.name if hasattr(plugin, 'name') else plugin.__class__.__name__

        if config:
            plugin_config = PluginConfig(
                name=plugin_name,
                enabled=config.get('enabled', True),
                priority=config.get('priority', 100),
                config=config
            )
        elif plugin_name in self.plugin_configs:
            plugin_config = self.plugin_configs[plugin_name]
        else:
            plugin_config = PluginConfig(name=plugin_name, enabled=True, priority=100)

        plugin._plugin_config = plugin_config

        if plugin_config.enabled:
            self.plugins.append(plugin)
            self.plugins.sort(key=lambda p: p._plugin_config.priority if hasattr(p, '_plugin_config') else 100)

    def load_plugins_from_config(self, config_path, conn):
        """从配置文件加载插件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                plugin_config = yaml.safe_load(f)

            for plugin_info in plugin_config.get('plugins', []):
                plugin_type = plugin_info.get('type')
                enabled = plugin_info.get('enabled', True)
                priority = plugin_info.get('priority', 100)

                if not enabled or not plugin_type:
                    continue

                try:
                    module_name, class_name = plugin_type.rsplit('.', 1)
                    import importlib
                    module = importlib.import_module(module_name)
                    plugin_class = getattr(module, class_name)
                    plugin = plugin_class(logger=conn.logger if hasattr(conn, 'logger') else None)
                    self.register_plugin(plugin, {'enabled': enabled, 'priority': priority, 'config': plugin_info})
                except Exception as e:
                    print(f"加载插件 {plugin_type} 失败: {e}")
        except Exception as e:
            print(f"加载插件配置失败: {e}")

    async def process_text(self, conn, text):
        """处理文本 - 支持三状态返回 (RELEASE/INTERCEPT/CLOSE)

        Returns:
            tuple: (result, action)
                - result: 处理后的文本或响应消息
                - action: PluginAction枚举值
        """
        processed_text = text

        for plugin in self.plugins:
            try:
                result = await plugin.pre_process_text(conn, processed_text)

                # 兼容旧格式 (result, bool) 和新格式 (result, PluginAction)
                if isinstance(result, tuple) and len(result) == 2:
                    if isinstance(result[1], bool):  # 旧格式
                        action = PluginAction.INTERCEPT if result[1] else PluginAction.RELEASE
                        processed_text, action = result[0], action
                    else:  # 新格式
                        processed_text, action = result
                else:
                    # 意外格式，跳过
                    continue

                # 处理不同状态并设置连接标志位
                if action == PluginAction.CLOSE:
                    conn.close_after_chat = True
                    return processed_text, PluginAction.CLOSE
                elif action == PluginAction.INTERCEPT:
                    conn.close_after_chat = False
                    return processed_text, PluginAction.INTERCEPT
                # RELEASE: 继续下一个插件，不设置标志位

            except Exception as e:
                if hasattr(conn, 'logger'):
                    conn.logger.error(f"插件 {plugin.name} 处理失败: {e}")
                continue

        return processed_text, PluginAction.RELEASE

    def get_plugins_info(self):
        """获取所有插件信息"""
        result = []
        for plugin in self.plugins:
            info = plugin.get_info()
            if hasattr(plugin, '_plugin_config'):
                info['enabled'] = plugin._plugin_config.enabled
                info['priority'] = plugin._plugin_config.priority
            result.append(info)
        return result

    def get_all_plugins_count(self):
        """获取插件总数"""
        return len(self.plugin_configs) if self.plugin_configs else len(self.plugins)

    def is_plugin_enabled(self, plugin_name):
        """检查插件是否启用"""
        if plugin_name in self.plugin_configs:
            return self.plugin_configs[plugin_name].enabled
        return any(hasattr(p, 'name') and p.name == plugin_name for p in self.plugins)