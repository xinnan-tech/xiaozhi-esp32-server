import os
import argparse
from ruamel.yaml import YAML
from collections.abc import Mapping
from core.utils.util import read_config, get_project_dir

default_config_file = "config.yaml"


def get_config_file():
    global default_config_file
    # 判断是否存在私有的配置文件
    config_file = default_config_file
    if os.path.exists(get_project_dir() + "data/." + default_config_file):
        config_file = "data/." + default_config_file
    return config_file


def load_config():
    """加载配置文件"""
    parser = argparse.ArgumentParser(description="Server configuration")
    config_file = get_config_file()
    parser.add_argument("--config_path", type=str, default=config_file)
    args = parser.parse_args()
    return read_config(args.config_path)


def update_config(config):
    yaml = YAML()
    yaml.preserve_quotes = True
    """将配置保存到YAML文件"""
    with open(get_config_file(), 'w') as f:
        yaml.dump(config, f)


def find_missing_keys(new_config, old_config, parent_key=''):
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
                value,
                old_config[key],
                parent_key=full_path
            )
            missing_keys.extend(sub_missing)

    return missing_keys


def check_config_file():
    old_config_file = get_config_file()
    global default_config_file
    if not old_config_file.startswith('data'):
        return
    old_config = read_config(get_project_dir() + old_config_file)
    new_config = read_config(get_project_dir() + default_config_file)
    # 查找缺失的配置项
    missing_keys = find_missing_keys(new_config, old_config)

    if missing_keys:
        error_msg = "您的配置文件太旧了，缺少了：\n"
        error_msg += "\n".join(f"- {key}" for key in missing_keys)
        error_msg += "\n建议您：\n"
        error_msg += "1、备份data/.config.yaml文件\n"
        error_msg += "2、将根目录的config.yaml文件复制到data下，重命名为.config.yaml\n"
        error_msg += "3、将密钥逐个复制到新的配置文件中\n"
        raise ValueError(error_msg)
