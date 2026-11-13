"""出厂配置与 provider 实现之间的一致性护栏。

config.yaml 是出厂默认配置，每个 provider 段（Memory/LLM/TTS/...）下的每个键
都对应一个可选的 provider 实现。两边一旦脱节，就会出现两种坏情况：

1. 配置里有、实现里没有 —— 用户选了会在 create_instance 阶段报
   "不支持的服务类型"。
2. 实现里有、配置里没有 —— 用户想选它，却要么找不到入口，要么在连接初始化
   阶段直接 KeyError（core/connection.py 里是
   ``self.config["Memory"][selected_module["Memory"]]["type"]``）。

Memory 段历史上踩过第 2 种：``mem_report_only`` 的实现在
core/providers/memory/mem_report_only/ 里，core/connection.py 也显式处理了它，
但 config.yaml 的 Memory 段没有对应配置块 —— 只要在 selected_module 里选了它，
连接初始化就会 KeyError，服务起不来。

这里把上面两条不变量钉死。
"""
from __future__ import annotations

import os

import pytest

from config.config_loader import get_project_dir, read_config

# 各模块的 provider 发现方式：
#   "dir"  —— 目录式：core/providers/<mod>/<type>/<type>.py
#   "file" —— 文件式：core/providers/<mod>/<type>.py
MODULES = [
    ("Intent", "intent", "dir"),
    ("Memory", "memory", "dir"),
    ("LLM", "llm", "dir"),
    ("ASR", "asr", "file"),
    ("TTS", "tts", "file"),
    ("VAD", "vad", "file"),
    ("VLLM", "vllm", "file"),
]

# 目录式模块里，一个实现目录通常只服务一个 provider（目录名 == 配置键 ==
# type）。LLM 是例外：core/providers/llm/openai/ 被 ChatGLMLLM、DoubaoLLM
# 等多个配置键共用，所以「实现 -> 配置」的反向检查只对一一对应的模块做。
ONE_TO_ONE_MODULES = ("Memory",)


@pytest.fixture(scope="module")
def default_config():
    """出厂的 config.yaml（未经 data/.config.yaml 覆盖）。"""
    return read_config(get_project_dir() + "config.yaml")


def _impl_path(mod: str, style: str, type_name: str) -> str:
    """provider 实现的绝对路径。"""
    root = get_project_dir()
    if style == "dir":
        return os.path.join(root, "core", "providers", mod, type_name, f"{type_name}.py")
    return os.path.join(root, "core", "providers", mod, f"{type_name}.py")


def test_selected_module_provider_is_configured(default_config):
    """selected_module 里选中的 provider 必须在对应配置段里存在。

    core/connection.py 初始化各模块时都是直接下标取配置
    （self.config["Memory"][selected_module["Memory"]]["type"]），
    配置段里缺这个键就是启动期 KeyError。
    """
    selected = default_config.get("selected_module") or {}
    for module in ("VAD", "ASR", "LLM", "VLLM", "TTS", "Memory", "Intent"):
        name = selected.get(module)
        assert name, f"selected_module.{module} 没有设置"
        block = (default_config.get(module) or {}).get(name)
        assert block is not None, (
            f"selected_module.{module} = {name}，"
            f"但 config.yaml 里没有 {module}.{name} 配置块"
        )


@pytest.mark.parametrize(
    "section,mod,style", MODULES, ids=[section for section, _, _ in MODULES]
)
def test_every_configured_provider_has_implementation(default_config, section, mod, style):
    """配置里的每个 provider，type 字段都必须指向真实存在的实现。

    覆盖「配置有、实现没有」：用户选了会在 create_instance 阶段报
    "不支持的服务类型"。
    """
    for name, block in (default_config.get(section) or {}).items():
        if not isinstance(block, dict):
            continue
        type_name = block.get("type", name)
        path = _impl_path(mod, style, type_name)
        assert os.path.exists(path), (
            f"{section}.{name} 的 type={type_name} 找不到实现文件 {path}"
        )


@pytest.mark.parametrize("section", ONE_TO_ONE_MODULES)
def test_every_implemented_provider_is_configured(default_config, section):
    """实现里有的 provider，配置里必须也有一份。

    覆盖「实现有、配置没有」：这类 provider 用户根本没法从出厂配置里选到，
    一旦有人手动选了就会在连接初始化阶段 KeyError。

    mem_report_only 就是这么漏掉的。
    """
    mod = section.lower()
    providers_dir = os.path.join(get_project_dir(), "core", "providers", mod)
    impls = sorted(
        name
        for name in os.listdir(providers_dir)
        if os.path.isfile(os.path.join(providers_dir, name, f"{name}.py"))
    )
    assert impls, f"core/providers/{mod} 下没找到任何 provider 实现"

    for name in impls:
        block = (default_config.get(section) or {}).get(name)
        assert block is not None, (
            f"core/providers/{mod}/{name} 有实现，"
            f"但 config.yaml 的 {section} 段没有 {name} 配置块"
        )
        assert block.get("type", name) == name, (
            f"config.yaml 的 {section}.{name}.type 应该是 {name}，"
            f"实际是 {block.get('type')}"
        )
