"""Pytest configuration — must run BEFORE any test imports project modules.

Adds the xiaozhi-server directory to sys.path so the existing implicit
relative imports (`from core.utils.textUtils import ...`) resolve.
"""
import sys
import types
from pathlib import Path

import yaml

# Windows console 默认 GBK 编码，emoji / 中文 print 会炸；强制 UTF-8
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
_CUSTOM_CONFIG = _PROJECT_ROOT / "data" / ".config.yaml"


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


def _fail_full_module_deployment() -> None:
    """检测到全模块部署时直接终止 pytest（fail-fast）。

    全模块部署下 manager-api 的 ``server.secret`` 是匿名 token，没
    ``sys:role:superAdmin`` 权限拿不到 LLM/TTS/Memory 的完整
    configJson（含 api_key），所以真发请求测试无法跑通。
    即使强行跑，部分模块会静默 skip，掩盖了「环境未就绪」的真相
    —— 出问题时难以定位是代码 bug 还是配置缺失。

    所以这里直接 fail-fast，exit code = 2（环境问题），让用户在
    pytest 输出里就明确知道要切单模块，而不是跑出"一堆 skip + 几
    个 pass"的迷惑结果。

    切换步骤：
      1. manager-web → 参数管理 → 模型配置，把 LLM/TTS/Memory 的
         configJson（api_key/base_url/model_name 等）抄出来
      2. 写到 data/.config.yaml（结构跟 config.yaml 一致）
      3. 清空 data/.config.yaml 里的 manager-api 整块
      4. 重跑 pytest
    """
    import sys

    message = (
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
        "[conftest] ============================================================"
    )
    print(message, file=sys.stderr, flush=True)
    sys.exit(2)


# 读 data/.config.yaml 仅用于「检测是否全模块部署」
_original_custom_data = (
    yaml.safe_load(_CUSTOM_CONFIG.read_text(encoding="utf-8")) or {}
    if _CUSTOM_CONFIG.exists()
    else {}
)

_api_cfg = _original_custom_data.get("manager-api", {})
_has_api_url = bool(_api_cfg.get("url"))
_has_api_secret = bool(_api_cfg.get("secret")) and "你" not in str(
    _api_cfg.get("secret", "")
)
_is_full_module = _has_api_url and _has_api_secret

# 永远走文件合并：单模块直接用，全模块走兜底（API key 缺失 → 真请求测试 skip）
CONFIG: dict = _load_via_file_merge()

if _is_full_module:
    _fail_full_module_deployment()
else:
    print("[conftest] OK: 单模块部署（文件合并配置）")


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
# 启动校验：5 个核心模块必须全部配齐才能跑 pytest
# （放在文件末尾是因为依赖 CONFIG / has_real_key，所有 helper 定义完后调用）
# ---------------------------------------------------------------------------
_REQUIRED_MODULES = ("ASR", "LLM", "TTS", "Memory", "VAD")
# secret-like 字段：必须有真值才算配齐
# - api_key / token / access_token / authorization / secret_key：通用鉴权
# - app_id / app_secret：豆包等
# - bot_id / user_id：CozeLLM 特殊（不用 api_key）
# - 客户端 SSL/TLS 证书：少用，先列上
_SECRET_FIELDS = (
    "api_key", "token", "access_token", "authorization",
    "secret_key", "access_key", "app_id", "app_secret",
    "bot_id", "user_id",
)


def _check_modules_ready() -> None:
    """检查 5 个核心模块是否都配齐可跑真请求。

    设计原则：**pytest 跑出来不能是骗人的**。如果某个模块没配齐，
    真请求测试会 skip，pytest 退出码仍为 0，CI 看起来"全过"——
    但实际上关键模块没跑。**自动 merge 链路下这是真风险**。

    所以 conftest 启动时校验：ASR/LLM/TTS/Memory/VAD 五个模块都要：
    1. 在 ``selected_module`` 里被选中（没被选中 = dev 没想测它）
    2. 在 ``cfg[module]`` 里有完整 provider 配置
    3. 配置里至少有一个 secret-like 字段（api_key/token/...）非占位符

    本地模型 provider（FunASR/SileroVAD/nomem）没有 secret 字段，
    通过校验；云 API provider（豆包/智谱/通义）必须填真 key。

    任意一项不满足 → sys.exit(3)，明确告诉 dev 缺什么。
    """
    problems: list[str] = []
    selected = CONFIG.get("selected_module") or {}
    for module in _REQUIRED_MODULES:
        provider_name = selected.get(module)
        if not provider_name:
            problems.append(
                f"{module} 未在 selected_module 配置（dev 漏选）"
            )
            continue
        cfg = CONFIG.get(module, {}).get(provider_name)
        if not cfg:
            problems.append(
                f"{module}.{provider_name} 配置缺失（CFG 字典里没这个 provider）"
            )
            continue
        # 校验 secret-like 字段：
        # - 配置里没任何 secret 字段 → 本地模型（FunASR/nomem/SileroVAD）合法，放过
        # - 有 secret 字段但全是占位符 → dev 没填真 key，拒收
        secret_keys_present = [k for k in _SECRET_FIELDS if k in cfg]
        if secret_keys_present and not any(
            has_real_key(cfg, k) for k in secret_keys_present
        ):
            problems.append(
                f"{module}.{provider_name} 的 secret 字段"
                f"{secret_keys_present} 全是占位符（dev 没填真 key）"
            )
    if problems:
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


_check_modules_ready()
