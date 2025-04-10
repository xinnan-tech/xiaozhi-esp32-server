import os
import argparse
from ruamel.yaml import YAML
from collections.abc import Mapping
from core.utils.util import read_config, get_project_dir

default_config_file = "config.yaml"
read_config_from_api = False


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


def get_config_file():
    global default_config_file
    global read_config_from_api
    """获取配置文件路径，优先使用私有配置文件（若存在）。

    Returns:
       str: 配置文件路径（相对路径或默认路径）
    """
    config_file = default_config_file
    if os.path.exists(get_project_dir() + "data/." + default_config_file):
        config_file = "data/." + default_config_file
        config = read_config(config_file)
        """如果存在manager-api，则使用manager-api的配置"""
        if config.get("manager-api", {}).get("url"):
            read_config_from_api = True
    return config_file


def load_config():
    """加载配置文件"""
    parser = argparse.ArgumentParser(description="Server configuration")
    config_file = get_config_file()

    parser.add_argument("--config_path", type=str, default=config_file)
    args = parser.parse_args()
    config = read_config(args.config_path)
    # 初始化目录
    ensure_directories(config)
    return config


def update_config(config):
    yaml = YAML()
    yaml.preserve_quotes = True
    """将配置保存到YAML文件"""
    with open(get_config_file(), "w") as f:
        yaml.dump(config, f)


def find_missing_keys(new_config, old_config, parent_key=""):
    """
    递归查找缺失的配置项
    返回格式：[缺失配置路径]
    """
    missing_keys = []

    if not isinstance(new_config, Mapping):
        return missing_keys

    for key, value in new_config.items():
        # 构建当前配置路径
        full_path = f"{parent_key}.{key}" if parent_key else key

        # 检查键是否存在
        if key not in old_config:
            missing_keys.append(full_path)
            continue

        # 递归检查嵌套字典
        if isinstance(value, Mapping):
            sub_missing = find_missing_keys(
                value, old_config[key], parent_key=full_path
            )
            missing_keys.extend(sub_missing)
    return missing_keys


def check_config_file():
    old_config_file = get_config_file()
    global default_config_file
    global read_config_from_api
    if not "data" in old_config_file:
        return
    old_config = read_config(get_project_dir() + old_config_file)
    new_config = read_config(get_project_dir() + default_config_file)
    # 查找缺失的配置项
    missing_keys = find_missing_keys(new_config, old_config)
    if read_config_from_api:
        missing_keys = remove_api_config(missing_keys)

    if missing_keys:
        missing_keys_str = "\n".join(f"- {key}" for key in missing_keys)

        if read_config_from_api:
            error_msg = "您的配置文件太旧了，缺少了：\n"
            error_msg += missing_keys_str
            error_msg += "\n建议您：\n"
            error_msg += "1、备份data/.config.yaml文件\n"
            error_msg += (
                "2、将根目录的config.yaml文件复制到data下，重命名为.config.yaml\n"
            )
            error_msg += "3、将密钥逐个复制到新的配置文件中\n"
        else:
            error_msg = "您的服务器配置和本地配置不一致，缺少了：\n"
            error_msg += missing_keys_str
            error_msg += "\n建议您：\n"
            error_msg += "1、保持manager-api和xiaozhi-server版本一致\n"
            error_msg += "2、或手动恢复被删除的配置\n"
        raise ValueError(error_msg)


def remove_api_config(missing_keys):
    """从缺失配置列表中移除API相关的配置项"""
    ignore_keys = {
        "server.auth",
        "module_test",
        "prompt",
        "selected_module",
        "Intent",
        "Memory",
        "ASR",
        "VAD",
        "LLM",
        "TTS",
    }
    missing_keys = [key for key in missing_keys if key not in ignore_keys]
    return missing_keys
