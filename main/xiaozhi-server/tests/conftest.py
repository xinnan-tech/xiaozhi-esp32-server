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

# Windows console defaults to GBK encoding; emoji / Chinese print will crash, force UTF-8.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


# ---------------------------------------------------------------------------
# opuslib_next stub: enables import chain; actual audio calls will fail, handle with try/except in tests
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
# Config loading: always merge files
# ---------------------------------------------------------------------------
# Priority:
#   1. File pointed to by environment variable ``PYTEST_CONFIG_FILE`` (recommended - isolated test config)
#   2. data/.config.yaml (Production / Single-module deployment config)
_DEFAULT_CUSTOM = _PROJECT_ROOT / "data" / ".config.yaml"

# Fresh checkout / CI fallback: the real data/.config.yaml is gitignored, so
# without this the suite only passes on dev boxes that happen to have one.
# Fall back to the tracked test-only config (placeholder keys, empty
# manager-api block) so a clean clone runs the exact same provider tests.
_TESTDATA_CONFIG = Path(__file__).resolve().parent / "testdata" / "test-config.yaml"
if os.environ.get("PYTEST_CONFIG_FILE"):
    # Explicit override always wins, even if the path does not exist yet.
    _CUSTOM_CONFIG = Path(os.environ["PYTEST_CONFIG_FILE"])
elif _DEFAULT_CUSTOM.exists():
    _CUSTOM_CONFIG = _DEFAULT_CUSTOM
else:
    _CUSTOM_CONFIG = _TESTDATA_CONFIG


def _load_via_file_merge() -> dict:
    """Pure file merge: config.yaml + data/.config.yaml. Consistent with production single-module deployment."""
    from config.config_loader import merge_configs

    config: dict = {}
    default_path = _PROJECT_ROOT / "config.yaml"
    if default_path.exists():
        config = yaml.safe_load(default_path.read_text(encoding="utf-8")) or {}

    if _CUSTOM_CONFIG.exists():
        custom = yaml.safe_load(_CUSTOM_CONFIG.read_text(encoding="utf-8")) or {}
        config = merge_configs(config, custom)

    return config


# Full-module deployment check (fail-fast in any mode to avoid triggering remote APIs).
# Full module deployment causes ``load_config`` to fetch remotely via manager-api; pytest should not trigger this.
if _CUSTOM_CONFIG.exists():
    _raw_custom = yaml.safe_load(_CUSTOM_CONFIG.read_text(encoding="utf-8")) or {}
    _api_cfg = _raw_custom.get("manager-api", {})
    _has_url = bool(_api_cfg.get("url"))
    _has_secret = bool(_api_cfg.get("secret")) and "You" not in str(
        _api_cfg.get("secret", "")
    )
    if _has_url and _has_secret:
        print(
            "\n[conftest] ============================================================\n"
            "[conftest] FAIL: Full-module deployment detected (manager-api.url + secret configured), \n"
            "[conftest]       pytest does not support full-module deployment. \n"
            "[conftest] Reason: manager-api server.secret is an anonymous token, \n"
            "[conftest]       Missing sys:role:superAdmin permission, \n"
            "[conftest]       Cannot retrieve configJson (including api_key) for LLM/TTS/Memory. \n"
            "[conftest] Switch to single-module method: \n"
            "[conftest]   1) manager-web → Parameter Management → Model Config, \n"
            "[conftest] Copy the configJson for LLM/TTS/Memory\n"
            "[conftest]   2) Write to data/.config.yaml (structure matches config.yaml) \n"
            "[conftest]   3) Clear the entire manager-api block in data/.config.yaml \n"
            "[conftest]   4) Rerun pytest\n"
            "[conftest] ============================================================",
            flush=True,
        )
        sys.exit(2)


# Always use file merging: single modules use directly
CONFIG: dict = _load_via_file_merge()


# ---------------------------------------------------------------------------
# Key: Replace runtime config entry points like ``load_config`` / ``get_server_config`` with
# Return the pre-built CONFIG directly to avoid ``config.config_loader.load_config`` in
# During test runtime, re-read ``data/.config.yaml`` (default is full-module deployment config) and trigger.
# manager-api remote call.
# ---------------------------------------------------------------------------
async def _load_config_patched(*_args, **_kwargs):
    return CONFIG


async def _get_server_config_patched(*_args, **_kwargs):
    return None


def _init_service_noop(_config):
    """Prevent ``init_service`` from instantiating ``ManageApiClient``."""
    return None


import config.config_loader as _cl  # noqa: E402
import config.manage_api_client as _mac  # noqa: E402
import config.settings as _settings  # noqa: E402
import config.logger as _logger_mod  # noqa: E402

_cl.load_config = _load_config_patched
# data/.config.yaml is gitignored, so a fresh checkout (CI) has none: skip the
# deployment-file check and keep log config coming from the merged CONFIG above.
# config.logger binds these names at import time (via manage_api_client), so
# patch the already-imported references as well, not just the source modules.
_settings.check_config_file = lambda: None
_logger_mod.check_config_file = lambda: None
_logger_mod.load_config = _load_config_patched
_mac.init_service = _init_service_noop
_mac.get_server_config = _get_server_config_patched
# Clear ManageApiClient singleton to avoid prior instantiation triggered by other code.
_mac.ManageApiClient._instance = None
_mac.ManageApiClient._closed = True


# ---------------------------------------------------------------------------
# Configure access helper (test reference)
# ---------------------------------------------------------------------------
def get_provider_config(module: str, provider_name: str | None = None) -> dict:
    """ get the config dict for a specific provider.

    - provider_name=None: Use ``selected_module[module]``
    - Otherwise explicitly specified
    Return {} to indicate not configured.
    """
    if provider_name is None:
        provider_name = CONFIG.get("selected_module", {}).get(module)
    if not provider_name:
        return {}
    return CONFIG.get(module, {}).get(provider_name, {}) or {}


def get_selected_provider_name(module: str) -> str | None:
    return CONFIG.get("selected_module", {}).get(module)


def get_provider_type(module: str, provider_name: str | None = None) -> str | None:
    """ returns the actual type name required by ``create_instance`` (which may differ from the section name).

    Convention (from core/utils/modules_initialize.py): fall back to section name when type is missing.
    """
    cfg = get_provider_config(module, provider_name)
    if not cfg:
        return None
    return cfg.get("type") or (provider_name or get_selected_provider_name(module))


def has_real_key(config: dict, *keys: str) -> bool:
    """Any candidate key with a non-placeholder value is considered a valid key.

    Placeholder check: empty / "Your..." / contains "placeholder" / literal "none".
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
        if s.startswith("Your") or "placeholder" in s:
            continue
        return True
    return False


# ---------------------------------------------------------------------------
# Default mock mode: intercepts third-party HTTP/SDK network calls, allowing tests to run without real keys
# ---------------------------------------------------------------------------
LIVE_API_TESTS: bool = os.environ.get("RUN_LIVE_API_TESTS") == "1"

# List of third-party SDKs. No action needed in real mode (keep real imports).
# In mock mode, inject these names into sys.modules and provide exception classes / client placeholders.
_MOCKED_MODULES: tuple[str, ...] = (
    # Note: Real third-party packages like openai / httpx / requests are usually installed in the conda environment,
    # Shimming the entire module breaks submodules like ``openai.types`` / ``httpx.AsyncClient``
    # Parse. Only shim if the corresponding package is not installed (__getattr__ still follows the real import path).
    "vosk",
    "edge_tts",
    "elevenlabs",
    "mem0",
    "mem0ai",
    "freezegun",
)

# Force shim these packages even if installed - they break imports in the local model chain
# (funasr imports torch, long torch DLL path), or heavy GPU dependencies, mock cannot run.
_FORCE_SHIM_MODULES: tuple[str, ...] = (
    "funasr",
    "torch",
    "torchaudio",
    "modelscope",
)


def _try_import_real(name: str) -> bool:
    """ check if real third-party package is loadable (does not actually import, only checks importer.find_spec).

    Actively invoking ``__import__`` triggers package-level side effects (e.g., funasr importing torch); bypass it directly
    Check if the package is in sys.path / site-packages.
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
        if name == "edge_tts":
            # core/providers/tts/edge.py imports edge_tts.communicate explicitly
            # to monkey-patch WSS_URL; provide the submodule shim so the import
            # resolves in mock mode (same pattern as opuslib_next above).
            _comm = _ShimModule(f"{name}.communicate")
            shim.communicate = _comm
            sys.modules[f"{name}.communicate"] = _comm

    # Shorten asyncio.sleep to prevent retry loops from delaying execution.
    import asyncio

    async def _fast_sleep(_seconds):
        return None

    asyncio.sleep = _fast_sleep  # type: ignore[assignment]

    # Network layer mock: if real httpx is loaded, replace its AsyncClient.send with
    # Stub that immediately raises ConnectError, triggering ``_should_retry`` to reach ``raise``,
    # But avoid sending real requests. Live mode does not install this layer.
    if not LIVE_API_TESTS:
        try:
            import httpx as _httpx  # noqa: F401

            # Subclass the real clients so SDK wrappers that extend them
            # (e.g. openai's SyncHttpxClientWrapper) keep every other method;
            # only the actual send is intercepted.
            class _FakeAsyncClient(_httpx.AsyncClient):
                async def send(self, *args, **kwargs):
                    raise _httpx.ConnectError("MOCK: connect refused")

            class _FakeClient(_httpx.Client):
                def send(self, *args, **kwargs):
                    raise _httpx.ConnectError("MOCK: connect refused")

            _httpx.AsyncClient = _FakeAsyncClient  # type: ignore[misc]
            _httpx.Client = _FakeClient  # type: ignore[misc]
        except ImportError:
            pass

        # edge-tts talks over websockets/aiohttp, bypassing the httpx shim,
        # so patch its entrypoint: yield one empty audio chunk and no network.
        try:
            import edge_tts as _edge_tts

            class _FakeCommunicate:
                def __init__(self, text="", voice="", **kwargs):
                    self.text = text
                    self.voice = voice

                async def stream(self):
                    # one empty audio chunk: enough for the provider to create
                    # the output file without any real traffic
                    yield {"type": "audio", "data": b""}

            _edge_tts.Communicate = _FakeCommunicate  # type: ignore[misc]
        except ImportError:
            pass


if not LIVE_API_TESTS:
    _install_mock_layer()


# ---------------------------------------------------------------------------
# Live-mode startup validation: single-module deployment check completed early in file loading
# ---------------------------------------------------------------------------
if LIVE_API_TESTS:
    print("[conftest] OK: Single-module deployment (merged file config)")


_REQUIRED_MODULES = ("ASR", "LLM", "TTS", "Memory", "VAD")
_SECRET_FIELDS = (
    "api_key", "token", "access_token", "authorization",
    "secret_key", "access_key", "app_id", "app_secret",
    "bot_id", "user_id",
)


def _check_modules_ready() -> None:
    """In Live mode: all 5 core modules must be configured. In Mock mode, only print a soft warning."""
    problems: list[str] = []
    selected = CONFIG.get("selected_module") or {}
    for module in _REQUIRED_MODULES:
        provider_name = selected.get(module)
        if not provider_name:
            problems.append(f"{module} not found in selected_module config (dev selection missing)")
            continue
        cfg = CONFIG.get(module, {}).get(provider_name)
        if not cfg:
            problems.append(
                f"{module}.{provider_name} config missing (provider not found in CFG dict)"
            )
            continue
        secret_keys_present = [k for k in _SECRET_FIELDS if k in cfg]
        if secret_keys_present and not any(
            has_real_key(cfg, k) for k in secret_keys_present
        ):
            problems.append(
                f"secret field of {module}.{provider_name}"
                f"{secret_keys_present} are all placeholders (dev didn't fill in real keys)"
            )
    if not problems:
        return
    if LIVE_API_TESTS:
        msg = (
            "\n[conftest] ============================================================\n"
            "[conftest] FAIL: pytest requires all 5 core modules to be configured to run. \n"
            "[conftest] Missing/not ready items: \n"
            + "\n".join(f"[conftest]   - {p}" for p in problems)
            + "\n[conftest] must stub 5 modules in data/.config.yaml"
            "(ASR/LLM/TTS/Memory/VAD) must all be configured to run pytest.\n"
            "[conftest] ============================================================"
        )
        print(msg, file=sys.stderr, flush=True)
        sys.exit(3)
    print(
        "[conftest] NOTE: Default mock mode - the following modules are not fully configured, but pytest can still run: \n  - "
        + "\n  - ".join(problems)
        + "\n[conftest] Live request mode: export RUN_LIVE_API_TESTS=1 and configure fully before running.",
        flush=True,
    )


_check_modules_ready()


# ---------------------------------------------------------------------------
# Explicit marker: notify user of current mode in mock mode
# ---------------------------------------------------------------------------
if not LIVE_API_TESTS:
    print(
        "[conftest] MOCK mode (default): Third-party HTTP/SDK shims injected; no real requests sent. \n"
        "[conftest] Live request mode: export RUN_LIVE_API_TESTS=1 pytest tests/ -v",
        flush=True,
    )


import pytest  # noqa: E402  (after conftest hooks so pytest is initialised)


def pytest_collection_modifyitems(config, items):
    """In Live mode: tests marked with ``live_api`` require keys to run (otherwise skip)."""
    if LIVE_API_TESTS:
        return
    # Do not force skip in Mock mode: tests should run (using shim).
    return
