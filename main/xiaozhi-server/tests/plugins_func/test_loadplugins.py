"""插件自动导入机制的测试。

``core/connection.py`` 启动时会调 ``auto_import_modules("plugins_func.functions")``，
把 ``plugins_func/functions`` 下的模块逐个导入一遍。导入过程中各插件用
``@register_function`` 把自己登记进注册表。这段自动导入万一被删掉，
插件一个都不会被加载，工具链直接空掉，而且不报错，很难发现。这里守住这条链路。

早先这个文件整份跳过，理由是自动导入会拉起一串重量级依赖。CI 里
``data/.config.yaml`` 是现造的，那个理由已经不成立了。
"""
import sys

from plugins_func.loadplugins import auto_import_modules
from plugins_func.register import all_function_registry


def test_auto_import_loads_plugin_modules():
    """自动导入跑完之后，插件模块应该已经在 sys.modules 里。"""
    auto_import_modules("plugins_func.functions")

    assert "plugins_func.functions.get_time" in sys.modules
    assert "plugins_func.functions.get_weather" in sys.modules


def test_auto_import_registers_plugin_functions():
    """自动导入的时候，插件函数应该已经登记进注册表。"""
    auto_import_modules("plugins_func.functions")

    assert "get_lunar" in all_function_registry
    assert "get_weather" in all_function_registry
