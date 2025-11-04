import os
from config.config_loader import read_config, get_project_dir, load_config


default_config_file = "custom_config.yaml"
config_file_valid = False


def check_config_file():
    global config_file_valid
    if config_file_valid:
        return
    """
    简化的配置检查，仅提示用户配置文件的使用情况
    """
    custom_config_file = get_project_dir() + default_config_file
    if not os.path.exists(custom_config_file):
        raise FileNotFoundError(
            "找不到custom_config.yaml文件，请按教程确认该配置文件是否存在"
        )

    # 检查是否从API读取配置
    config = load_config()
    if config.get("read_config_from_api", False):
        print("从API读取配置")
        # 支持混合模式：API 优先，本地配置作为兜底
        # 允许同时存在 API 配置和本地 selected_module/role_id
    config_file_valid = True
