import os
import argparse
import yaml
from config.manage_api_client import init_service, get_server_config, get_agent_models


# 添加全局配置缓存
_config_cache = None


def get_project_dir():
    """获取项目根目录"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/"


def read_config(config_path):
    with open(config_path, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
    return config


def load_config():
    """加载配置文件"""
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    parser = argparse.ArgumentParser(description="Server configuration")
    config_file = get_config_file()

    parser.add_argument("--config_path", type=str, default=config_file)
    args = parser.parse_args()
    config = read_config(args.config_path)

    if config.get("manager-api", {}).get("url"):
        config = get_config_from_api(config)

    # 初始化目录
    ensure_directories(config)
    _config_cache = config
    return config


def get_config_file():
    """获取配置文件路径，优先使用私有配置文件（若存在）。

    Returns:
       str: 配置文件路径（相对路径或默认路径）
    """
    default_config_file = "config.yaml"
    config_file = default_config_file
    if os.path.exists(get_project_dir() + "data/." + default_config_file):
        config_file = "data/." + default_config_file
    return config_file


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
    if config.get("server"):
        config_data["server"] = {
            "ip": config["server"].get("ip", ""),
            "port": config["server"].get("port", ""),
        }
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
