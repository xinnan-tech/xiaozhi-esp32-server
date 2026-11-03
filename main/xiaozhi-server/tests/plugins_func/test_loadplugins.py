"""插件自动导入机制的测试。

``core/connection.py`` 启动时会调 ``auto_import_modules("plugins_func.functions")``，
把 ``plugins_func/functions`` 下的模块逐个导入一遍。导入过程中各插件用
``@register_function`` 把自己登记进注册表。这段自动导入万一被删掉，
插件一个都不会被加载，工具链直接空掉，而且不报错，很难发现。这里守住这条链路。

最后一条用例查的是 ``core/connection.py`` 的源码本身：自动导入这个动作做得对
不对，跟连接模块有没有真的调它，是两回事，两条都要守。

早先这个文件整份跳过，理由是自动导入会拉起一串重量级依赖。CI 里
``data/.config.yaml`` 是现造的，那个理由已经不成立了。
"""
import sys
from pathlib import Path

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


def test_connection_module_triggers_auto_import():
    """core/connection.py 模块加载时那次自动导入得在

    <p>
    这行被删掉或者改成注释，插件一个都不会被加载：启动不报错，工具链空掉，
    上面两条用例照样绿。这里查源码，盯住那一次调用。
    """
    import ast

    source_path = Path(__file__).resolve().parents[2] / "core" / "connection.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))

    imported_packages = []
    for node in tree.body:
        if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
            continue
        call = node.value
        func = call.func
        name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
        if name != "auto_import_modules":
            continue
        for arg in call.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                imported_packages.append(arg.value)

    assert "plugins_func.functions" in imported_packages, (
        "core/connection.py 模块加载时的那次自动导入不见了，"
        "插件不会被加载，工具链会空掉"
    )
