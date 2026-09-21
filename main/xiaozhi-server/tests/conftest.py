"""Pytest configuration — must run BEFORE any test imports project modules.

Adds the xiaozhi-server directory to sys.path so the existing implicit
relative imports (`from core.utils.textUtils import ...`) resolve.

External-API mock toggle (default: mocked)
-------------------------------------------
The dep-upgrade orchestrator and CI run this test suite *without* any
real API credentials. By default the tests construct the actual provider
objects from ``data/.config.yaml`` but route every network call through
a recording shim, so no traffic leaves the host.

Set ``RUN_LIVE_API_TESTS=1`` to opt in to real network calls. In that
mode the 5-module readiness check runs in strict form (any missing key
→ ``sys.exit(3)``), the mock shims are uninstalled, and tests hit the
real providers.

Configuration loading
---------------------
Always uses the file-merge path (``config.yaml`` + ``data/.config.yaml``).
``manager-api`` is intentionally NOT contacted — pytest must work in a
single-module deployment.
"""
from __future__ import annotations

import os
import sys
import types
from pathlib import Path

import yaml

# Windows console 默认 GBK 编码；emoji / 中文 print 会炸，强制 UTF-8。
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


# ---------------------------------------------------------------------------
# opuslib_next stub：让 import 链路通；真调音频会失败，测试自行 try/except
# ---------------------------------------------------------------------------
try:
    import opuslib_next  # noqa: F401
except Exception:
    _stub = types.ModuleType("opuslib_next")
    _stub.Encoder = type("Encoder", (), {"__init__": lambda *a, **kw: None})
    _stub.Decoder = type("Decoder", (), {"__init__": lambda *a, **kw: None})
    _stub.APPLICATION_AUDIO = 0
    _stub.OpusError = type("OpusError", (Exception,), {})
    _stub.constants = types.SimpleNamespace()
    sys.modules["opuslib_next"] = _stub
    for sub in ("api", "exceptions"):
        sys.modules[f"opuslib_next.{sub}"] = types.ModuleType(f"opuslib_next.{sub}")


# ---------------------------------------------------------------------------
# 配置加载：永远走文件合并
# ---------------------------------------------------------------------------
# 优先级：
#   1. 环境变量 ``PYTEST_CONFIG_FILE`` 指向的文件（推荐 — 隔离测试配置）
#   2. data/.config.yaml（生产 / 单模块部署配置）
_DEFAULT_CUSTOM = _PROJECT_ROOT / "data" / ".config.yaml"
_CUSTOM_CONFIG = Path(os.environ["PYTEST_CONFIG_FILE"]) if os.environ.get(
    "PYTEST_CONFIG_FILE"
) else _DEFAULT_CUSTOM


def _load_via_file_merge() -> dict:
    """纯文件合并：config.yaml + data/.config.yaml。和生产单模块部署一致。"""
    from config.config_loader import merge_configs

    config: dict = {}
    default_path = _PROJECT_ROOT / "config.yaml"
    if default_path.exists():
        config = yaml.safe_load(default_path.read_text(encoding="utf-8")) or {}

    if _CUSTOM_CONFIG.exists():
        custom = yaml.safe_load(_CUSTOM_CONFIG.read_text(encoding="utf-8")) or {}
        config = merge_configs(config, custom)

    return config


# 全模块部署检测（在任何模式下都 fail-fast，避免触发远程 API）。
# 全模块部署会让 ``load_config`` 走 manager-api 远程拉取，pytest 不应该触发。
if _CUSTOM_CONFIG.exists():
    _raw_custom = yaml.safe_load(_CUSTOM_CONFIG.read_text(encoding="utf-8")) or {}
    _api_cfg = _raw_custom.get("manager-api", {})
    _has_url = bool(_api_cfg.get("url"))
    _has_secret = bool(_api_cfg.get("secret")) and "你" not in str(
        _api_cfg.get("secret", "")
    )
    if _has_url and _has_secret:
        print(
            "\n[conftest] ============================================================\n"
            "[conftest] FAIL: 检测到全模块部署（manager-api.url + secret 已配置），\n"
            "[conftest]       pytest 不支持全模块部署。\n"
            "[conftest] 原因：manager-api 的 server.secret 是匿名 token，\n"
            "[conftest]       没有 sys:role:superAdmin 权限，\n"
            "[conftest]       拿不到 LLM/TTS/Memory 的 configJson（含 api_key）。\n"
            "[conftest] 切换到单模块的方法：\n"
            "[conftest]   1) manager-web → 参数管理 → 模型配置，\n"
            "[conftest]      把 LLM/TTS/Memory 的 configJson 抄出来\n"
            "[conftest]   2) 写到 data/.config.yaml（结构跟 config.yaml 一致）\n"
            "[conftest]   3) 清空 data/.config.yaml 里的 manager-api 整块\n"
            "[conftest]   4) 重跑 pytest\n"
            "[conftest] ============================================================",
            flush=True,
        )
        sys.exit(2)


# 永远走文件合并：单模块直接用
CONFIG: dict = _load_via_file_merge()


# ---------------------------------------------------------------------------
# 关键：把 ``load_config`` / ``get_server_config`` 等运行时配置入口替换成
# 直接返回我们已构建的 CONFIG，避免 ``config.config_loader.load_config`` 在
# 测试运行期间再次读取 ``data/.config.yaml``（默认是全模块部署配置）并触发
# manager-api 远程调用。
# ---------------------------------------------------------------------------
async def _load_config_patched(*_args, **_kwargs):
    return CONFIG


async def _get_server_config_patched(*_args, **_kwargs):
    return None


def _init_service_noop(_config):
    """阻止 ``init_service`` 实例化 ``ManageApiClient``。"""
    return None


import config.config_loader as _cl  # noqa: E402
import config.manage_api_client as _mac  # noqa: E402
_cl.load_config = _load_config_patched
_mac.init_service = _init_service_noop
_mac.get_server_config = _get_server_config_patched
# 清空 ManageApiClient 单例，避免前面已经被其它代码触发过实例化。
_mac.ManageApiClient._instance = None
_mac.ManageApiClient._closed = True


# ---------------------------------------------------------------------------
# 配置访问 helper（test 引用）
# ---------------------------------------------------------------------------
def get_provider_config(module: str, provider_name: str | None = None) -> dict:
    """拿某个 provider 的 config dict。

    - provider_name=None：取 ``selected_module[module]``
    - 否则显式指定
    返回 {} 表示没配。
    """
    if provider_name is None:
        provider_name = CONFIG.get("selected_module", {}).get(module)
    if not provider_name:
        return {}
    return CONFIG.get(module, {}).get(provider_name, {}) or {}


def get_selected_provider_name(module: str) -> str | None:
    return CONFIG.get("selected_module", {}).get(module)


def get_provider_type(module: str, provider_name: str | None = None) -> str | None:
    """返回 ``create_instance`` 真正需要的 type 名（与 section 名可能不同）。

    约定（来自 core/utils/modules_initialize.py）：type 不存在时回退到 section 名。
    """
    cfg = get_provider_config(module, provider_name)
    if not cfg:
        return None
    return cfg.get("type") or (provider_name or get_selected_provider_name(module))


def has_real_key(config: dict, *keys: str) -> bool:
    """任一候选 key 名下值不是占位符就算有真密钥。

    占位符判定：空 / "你的..." / 包含 "placeholder" / 字面 "none"。
    """
    if not config:
        return False
    for key in keys:
        val = config.get(key)
        if val is None:
            continue
        s = str(val).strip().lower()
        if not s or s == "none":
            continue
        if s.startswith("你的") or "placeholder" in s:
            continue
        return True
    return False


# ---------------------------------------------------------------------------
# 默认 mock 模式：拦截第三方 HTTP/SDK 网络调用，测试无须真密钥也能跑通
# ---------------------------------------------------------------------------
LIVE_API_TESTS: bool = os.environ.get("RUN_LIVE_API_TESTS") == "1"

# 第三方 SDK 列表。真实模式下不需要做任何事（保留真实 import）。
# Mock 模式下把这些名字塞进 sys.modules，并提供异常类 / 客户端占位。
_MOCKED_MODULES: tuple[str, ...] = (
    # 注：openai / httpx / requests 这些真实第三方包通常已装在 conda 环境，
    # shim 整个 module 会破坏 ``openai.types`` / ``httpx.AsyncClient`` 等子模块
    # 解析。仅当对应包没装时才 shim（__getattr__ 仍走真 import 路径）。
    "anthropic",
    "dashscope",
    "tencentcloud",
    "xunfei",
    "vosk",
    "edge_tts",
    "elevenlabs",
    "mem0",
    "mem0ai",
    "freezegun",
)

# 这些包即使装了也强制 shim — 它们要么本地模型链 import 时炸
# (funasr 引 torch、torch DLL 路径长)，要么是 GPU 重型依赖，mock 跑不动。
_FORCE_SHIM_MODULES: tuple[str, ...] = (
    "funasr",
    "torch",
    "torchaudio",
    "modelscope",
)


def _try_import_real(name: str) -> bool:
    """检查真实第三方包是否可加载（不真正 import，只检查 importer.find_spec）。

    主动 ``__import__`` 会触发包级副作用（funasr 引 torch 等），绕过它直接
    看包是否在 sys.path / site-packages 里。
    """
    import importlib.util

    spec = importlib.util.find_spec(name)
    return spec is not None


class _RecordingShim:
    """A no-op stand-in for any object reachable through a shimmed module.

    Acts as both a callable and an attribute container: every attribute
    access returns a callable that records the call and yields another
    shim. Used as a base class for fake exception classes so
    ``except httpx.ConnectError`` blocks evaluate correctly.
    """

    _calls: list = []

    def __init__(self, *_args, **_kwargs):
        pass

    def __getattr__(self, attr):
        def _record(*args, **kwargs):
            type(self)._calls.append((attr, args, kwargs))
            return _RecordingShim()

        return _record

    def __call__(self, *args, **kwargs):
        type(self)._calls.append(("__call__", args, kwargs))
        return _RecordingShim()


class _ShimModule(types.ModuleType):
    """PEP 562 module — any attribute access returns a recording shim."""

    def __getattr__(self, attr):
        if attr in ("__path__", "__loader__", "__spec__"):
            raise AttributeError(attr)
        # Cache so identity stays stable across accesses.
        value = _RecordingShim()
        setattr(self, attr, value)
        return value


def _install_mock_layer() -> None:
    """Insert PEP 562 shims for every third-party SDK in :data:`_MOCKED_MODULES`.

    Exception classes (e.g. ``httpx.ConnectError``) become ``_RecordingShim``
    subclasses — so ``except`` blocks match and ``isinstance`` checks pass.
    Common callable symbols (``Client`` / ``OpenAI`` / ``AutoModel``) are
    pre-bound to the shim type so ``Client(...)`` constructions succeed.

    If a real package is already importable (e.g. openai installed in conda),
    we leave it alone — shimming would break submodule resolution like
    ``openai.types``.
    """
    for name in list(_MOCKED_MODULES) + list(_FORCE_SHIM_MODULES):
        if name in sys.modules and isinstance(sys.modules[name], _ShimModule):
            continue
        if name not in _FORCE_SHIM_MODULES and _try_import_real(name):
            # Real package is available — use it. We'll patch network I/O
            # at the request layer in mock mode (see below).
            continue
        shim = _ShimModule(name)
        shim.OpenAI = _RecordingShim
        shim.AsyncOpenAI = _RecordingShim
        shim.Client = _RecordingShim
        shim.AsyncClient = _RecordingShim
        shim.AutoModel = _RecordingShim
        shim.completions = _RecordingShim()
        shim.chat = _RecordingShim()
        shim.exceptions = _ShimModule(f"{name}.exceptions")
        sys.modules[name] = shim
        sys.modules[f"{name}.exceptions"] = shim.exceptions

    # 短化 asyncio.sleep 避免重试循环拖时间。
    import asyncio

    async def _fast_sleep(_seconds):
        return None

    asyncio.sleep = _fast_sleep  # type: ignore[assignment]

    # 网络层 mock：如果真实 httpx 已加载，把它的 AsyncClient.send 替换成
    # 立即抛 ConnectError 的桩，触发 ``_should_retry`` 走到 ``raise``，
    # 但避免真发请求。Live 模式完全不安装这层。
    if not LIVE_API_TESTS:
        try:
            import httpx as _httpx  # noqa: F401

            class _FakeAsyncClient:
                def __init__(self, *args, **kwargs):
                    pass

                async def send(self, *args, **kwargs):
                    raise _httpx.ConnectError("MOCK: connect refused")

                async def aclose(self):
                    return None

            class _FakeClient:
                def __init__(self, *args, **kwargs):
                    pass

                def send(self, *args, **kwargs):
                    raise _httpx.ConnectError("MOCK: connect refused")

                def close(self):
                    return None

            _httpx.AsyncClient = _FakeAsyncClient  # type: ignore[misc]
            _httpx.Client = _FakeClient  # type: ignore[misc]
        except ImportError:
            pass


if not LIVE_API_TESTS:
    _install_mock_layer()


# ---------------------------------------------------------------------------
# Live-mode 启动校验：单模块部署检测已在文件加载早期完成
# ---------------------------------------------------------------------------
if LIVE_API_TESTS:
    print("[conftest] OK: 单模块部署（文件合并配置）")


_REQUIRED_MODULES = ("ASR", "LLM", "TTS", "Memory", "VAD")
_SECRET_FIELDS = (
    "api_key", "token", "access_token", "authorization",
    "secret_key", "access_key", "app_id", "app_secret",
    "bot_id", "user_id",
)


def _check_modules_ready() -> None:
    """Live 模式下：5 个核心模块必须配齐。Mock 模式下只打印 soft warning。"""
    problems: list[str] = []
    selected = CONFIG.get("selected_module") or {}
    for module in _REQUIRED_MODULES:
        provider_name = selected.get(module)
        if not provider_name:
            problems.append(f"{module} 未在 selected_module 配置（dev 漏选）")
            continue
        cfg = CONFIG.get(module, {}).get(provider_name)
        if not cfg:
            problems.append(
                f"{module}.{provider_name} 配置缺失（CFG 字典里没这个 provider）"
            )
            continue
        secret_keys_present = [k for k in _SECRET_FIELDS if k in cfg]
        if secret_keys_present and not any(
            has_real_key(cfg, k) for k in secret_keys_present
        ):
            problems.append(
                f"{module}.{provider_name} 的 secret 字段"
                f"{secret_keys_present} 全是占位符（dev 没填真 key）"
            )
    if not problems:
        return
    if LIVE_API_TESTS:
        msg = (
            "\n[conftest] ============================================================\n"
            "[conftest] FAIL: pytest 要求 5 个核心模块全部配齐才能跑。\n"
            "[conftest] 缺失/未就绪项：\n"
            + "\n".join(f"[conftest]   - {p}" for p in problems)
            + "\n[conftest] 必须在 data/.config.yaml 里把 5 个模块"
            "（ASR/LLM/TTS/Memory/VAD）都配齐才能跑 pytest。\n"
            "[conftest] ============================================================"
        )
        print(msg, file=sys.stderr, flush=True)
        sys.exit(3)
    print(
        "[conftest] NOTE: 默认 mock 模式 — 下列模块未配齐，但 pytest 仍可跑：\n  - "
        + "\n  - ".join(problems)
        + "\n[conftest] 真请求模式：export RUN_LIVE_API_TESTS=1 且配齐后再跑。",
        flush=True,
    )


_check_modules_ready()


# ---------------------------------------------------------------------------
# 显式标记：mock 模式下提示用户当前模式
# ---------------------------------------------------------------------------
if not LIVE_API_TESTS:
    print(
        "[conftest] MOCK 模式（默认）：第三方 HTTP/SDK 已注入 shim，不发真请求。\n"
        "[conftest] 真请求模式：export RUN_LIVE_API_TESTS=1 pytest tests/ -v",
        flush=True,
    )


import pytest  # noqa: E402  (after conftest hooks so pytest is initialised)


def pytest_collection_modifyitems(config, items):
    """Live 模式下：``live_api`` 标记的测试必须配齐密钥才能跑（否则 skip）。"""
    if LIVE_API_TESTS:
        return
    # Mock 模式下不强行 skip：测试应该都能跑（用 shim）。
    return
