import os
import yaml
from collections.abc import Mapping
from config.manage_api_client import init_service, get_server_config, get_agent_models
from dotenv import load_dotenv

def get_project_dir():
    """获取项目根目录"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/"


def read_config(config_path):
    with open(config_path, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
    return config


def load_config():
    """加载配置文件"""
    from core.utils.cache.manager import cache_manager, CacheType

    # 检查缓存
    cached_config = cache_manager.get(CacheType.CONFIG, "main_config")
    if cached_config is not None:
        return cached_config

    # default_config_path = get_project_dir() + "config.yaml"
    custom_config_path = get_project_dir() + "custom_config.yaml"

    # 加载默认配置
    # default_config = read_config(default_config_path)
    config = read_config(custom_config_path)
    config["read_config_from_live_agent_api"] = True
    # load environment variables
    load_dotenv()
    # tts
    select_tts_module = config["selected_module"]["TTS"]
    if os.environ.get("REGION") == "LOCAL" and select_tts_module == "FishSpeech":
        config["TTS"][select_tts_module]["api_key"] = os.environ.get("FISH_API_KEY")
    # asr
    select_asr_module = config["selected_module"]["ASR"]
    if os.environ.get("REGION") == "LOCAL" and select_asr_module == "GroqASR":
        config["ASR"][select_asr_module]["api_key"] = os.environ.get("GROQ_API_KEY")
    # llm
    select_llm_module = config["selected_module"]["LLM"]
    if os.environ.get("REGION") == "LOCAL" and select_llm_module == "GroqLLM":
        config["LLM"][select_llm_module]["api_key"] = os.environ.get("GROQ_API_KEY")
    # if custom_config.get("manager-api", {}).get("url"):
    #     config = get_config_from_api(custom_config)
    # else:
    #     # 合并配置
    #     config = merge_configs(default_config, custom_config)
    # 初始化目录
    ensure_directories(config)

    # 缓存配置
    cache_manager.set(CacheType.CONFIG, "main_config", config)
    return config


def get_config_from_api(config):
    """从Java API获取配置"""
    # 初始化API客户端
    init_service(config)

    # 获取服务器配置
    config_data = get_server_config()
    if config_data is None:
        raise Exception("Failed to fetch server config from API")

    config_data["read_config_from_api"] = True
    config_data["manager-api"] = {
        "url": config["manager-api"].get("url", ""),
        "secret": config["manager-api"].get("secret", ""),
    }
    # server的配置以本地为准
    if config.get("server"):
        config_data["server"] = {
            "ip": config["server"].get("ip", ""),
            "port": config["server"].get("port", ""),
            "http_port": config["server"].get("http_port", ""),
            "vision_explain": config["server"].get("vision_explain", ""),
            "auth_key": config["server"].get("auth_key", ""),
        }
    # 如果服务器没有prompt_template，则从本地配置读取
    if not config_data.get("prompt_template"):
        config_data["prompt_template"] = config.get("prompt_template")
    return config_data


def get_private_config_from_api(config, device_id, client_id):
    """从Java API获取私有配置"""
    return get_agent_models(device_id, client_id, config["selected_module"])


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
        if config.get(module) is None:
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
