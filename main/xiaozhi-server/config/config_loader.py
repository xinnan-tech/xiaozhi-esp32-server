import os
import asyncio
import yaml
from collections.abc import Mapping
from config.manage_api_client import (
    init_service,
    get_server_config,
    get_agent_models,
    get_correct_words,
    DeviceNotFoundException,
    DeviceBindException,
)


def get_project_dir():
    """获取项目根目录"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/"


def read_config(config_path):
    with open(config_path, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
    return config


async def load_config():
    """加载配置文件"""
    from core.utils.cache.manager import cache_manager, CacheType

    # 检查缓存
    cached_config = cache_manager.get(CacheType.CONFIG, "main_config")
    if cached_config is not None:
        return cached_config

    default_config_path = get_project_dir() + "config.yaml"
    custom_config_path = get_project_dir() + "data/.config.yaml"

    # 加载默认配置
    default_config = read_config(default_config_path)
    custom_config = read_config(custom_config_path)

    if custom_config.get("manager-api", {}).get("url"):
        config = await get_config_from_api_async()
    else:
        # 合并配置
        config = merge_configs(default_config, custom_config)
    # 初始化目录
    ensure_directories(config)

    # 缓存配置
    cache_manager.set(CacheType.CONFIG, "main_config", config)
    return config


async def get_config_from_api_async():
    """从Java API获取配置（异步版本），本地配置逐键覆盖上去

    本地配置在这里自己读，不接受调用方传进来：调用方手里只有上一次合并
    完的结果，拿它当"本地"会把旧值盖回这次新拉到的响应，改配置不生效。
    """
    local_config = read_config(get_project_dir() + "data/.config.yaml") or {}

    # 初始化API客户端
    init_service(local_config)

    # 获取服务器配置
    config_data = await get_server_config()
    if config_data is None:
        raise Exception("Failed to fetch server config from API")

    config_data["read_config_from_api"] = True
    config_data["manager-api"] = {
        "url": local_config.get("manager-api", {}).get("url", ""),
        "secret": local_config.get("manager-api", {}).get("secret", ""),
    }
    server_config = config_data.setdefault("server", {})
    # 认证开关以智控台的参数管理为准，这里只补默认值。
    # 不能重建整个 auth，否则接口返回的 allowed_devices、activation_codes
    # 这些字段会被抹掉，智控台部署下等于配置写了不生效
    server_auth = server_config.setdefault("auth", {})
    server_auth.setdefault("enabled", False)
    # 智控台只下发 enabled 这一个键，本地配的白名单、激活码、吊销线、有效期
    # 得逐键并进去。整段跳过的话它们在官方全模块部署里一个都用不了，
    # 而本地这边没有任何提示，配了等于没配。
    # 智控台哪天开始下发这些键，以智控台为准
    for key, value in ((local_config.get("server") or {}).get("auth") or {}).items():
        if key != "enabled":
            server_auth.setdefault(key, value)

    # server 的其余配置以本地为准，但只覆盖本地显式写过的字段。
    # 整块替换会把接口返回的 cors、websocket 等一并吞掉。
    # auth 例外，它归智控台管，在上面单独合并
    # 注意 auth_key 在 server 下、不在 server.auth 里，它归这一段管；
    # 而 config.yaml 里根本没有 auth_key 这一行，默认部署下压根不参与合并，
    # 靠 app.py 回落到 manager-api.secret。要改它得显式写进 data/.config.yaml
    for key, value in (local_config.get("server") or {}).items():
        if key != "auth":
            server_config[key] = value

    # 如果服务器没有prompt_template，则从本地配置读取
    if not config_data.get("prompt_template"):
        config_data["prompt_template"] = local_config.get("prompt_template")
    return config_data


async def get_private_config_from_api(config, device_id, client_id):
    """从Java API获取私有配置"""
    results = await asyncio.gather(
        get_agent_models(device_id, client_id, config["selected_module"]),
        get_correct_words(device_id),
        return_exceptions=True,
    )
    agent_result = results[0]
    correct_words = results[1] if not isinstance(results[1], Exception) else None

    # 抛出业务异常
    if isinstance(agent_result, DeviceNotFoundException):
        raise agent_result
    if isinstance(agent_result, DeviceBindException):
        raise agent_result

    private_config = agent_result if not isinstance(agent_result, Exception) else {}
    if correct_words:
        private_config["correct_words"] = correct_words
    return private_config


def ensure_directories(config):
    """确保所有配置路径存在"""
    dirs_to_create = set()
    project_dir = get_project_dir()  # 获取项目根目录
    # 日志文件目录
    log_dir = config.get("log", {}).get("log_dir", "tmp")
    dirs_to_create.add(os.path.join(project_dir, log_dir))

    # ASR/TTS模块输出目录
    for module in ["ASR", "TTS"]:
        if config.get(module) is None:
            continue
        for provider in config.get(module, {}).values():
            output_dir = provider.get("output_dir", "")
            if output_dir:
                dirs_to_create.add(output_dir)

    # 根据selected_module创建模型目录
    selected_modules = config.get("selected_module", {})
    for module_type in ["ASR", "LLM", "TTS"]:
        selected_provider = selected_modules.get(module_type)
        if not selected_provider:
            continue
        if config.get(module_type) is None:
            continue
        if config.get(selected_provider) is None:
            continue
        provider_config = config.get(module_type, {}).get(selected_provider, {})
        output_dir = provider_config.get("output_dir")
        if output_dir:
            full_model_dir = os.path.join(project_dir, output_dir)
            dirs_to_create.add(full_model_dir)

    # 统一创建目录（保留原data目录创建）
    for dir_path in dirs_to_create:
        try:
            os.makedirs(dir_path, exist_ok=True)
        except PermissionError:
            print(f"警告：无法创建目录 {dir_path}，请检查写入权限")


def merge_configs(default_config, custom_config):
    """
    递归合并配置，custom_config优先级更高

    Args:
        default_config: 默认配置
        custom_config: 用户自定义配置

    Returns:
        合并后的配置
    """
    if not isinstance(default_config, Mapping) or not isinstance(
        custom_config, Mapping
    ):
        return custom_config

    merged = dict(default_config)

    for key, value in custom_config.items():
        if (
            key in merged
            and isinstance(merged[key], Mapping)
            and isinstance(value, Mapping)
        ):
            merged[key] = merge_configs(merged[key], value)
        else:
            merged[key] = value

    return merged
