import os
from collections.abc import Mapping
from config.config_loader import read_config, get_project_dir, load_config

default_config_file = "config.yaml"


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
    old_config_file = get_project_dir() + "data/." + default_config_file
    if not os.path.exists(old_config_file):
        return
    old_config = load_config()
    new_config = read_config(get_project_dir() + default_config_file)
    # 查找缺失的配置项
    missing_keys = find_missing_keys(new_config, old_config)
    read_config_from_api = old_config.get("read_config_from_api", False)
    if read_config_from_api:
        old_config_origin = read_config(old_config_file)
        if old_config_origin.get("selected_module") is not None:
            missing_keys_str = "\n".join(f"- {key}" for key in missing_keys)
            error_msg = "您的配置文件好像既包含智控台的配置又包含本地配置：\n"
            error_msg += "\n建议您：\n"
            error_msg += "1、将根目录的config_from_api.yaml文件复制到data下，重命名为.config.yaml\n"
            error_msg += "2、按教程配置好接口地址和密钥\n"
            raise ValueError(error_msg)
        return

    if missing_keys:
        missing_keys_str = "\n".join(f"- {key}" for key in missing_keys)
        error_msg = "您的配置文件太旧了，缺少了：\n"
        error_msg += missing_keys_str
        error_msg += "\n建议您：\n"
        error_msg += "1、备份data/.config.yaml文件\n"
        error_msg += "2、将根目录的config.yaml文件复制到data下，重命名为.config.yaml\n"
        error_msg += "3、将密钥逐个复制到新的配置文件中\n"
        raise ValueError(error_msg)
