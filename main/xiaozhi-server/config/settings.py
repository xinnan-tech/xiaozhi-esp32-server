import os
import asyncio
from dotenv import load_dotenv
from config.config_loader import read_config, get_project_dir, load_config

# Carrega as variáveis do arquivo .env para o ambiente Python
load_dotenv()
DEFAULT_AGENT_ID = os.getenv("DEFAULT_AGENT_ID", "a69fbf960e9840f09a2ba12dd3ff4c15")

default_config_file = "config.yaml"
config_file_valid = False

def check_config_file():
    global config_file_valid
    if config_file_valid:
        return

    # os.path.join garante a montagem correta de caminhos no Linux/Docker
    custom_config_file = os.path.join(get_project_dir(), "data", f".{default_config_file}")
    
    if not os.path.exists(custom_config_file):
        raise FileNotFoundError(
            "找不到data/.config.yaml文件，请按教程确认该配置文件是否存在"
        )

    # 检查是否从API读取配置
    config = asyncio.run(load_config())
    if config.get("read_config_from_api", False):
        print("从API读取配置")
        old_config_origin = read_config(custom_config_file)
        if old_config_origin.get("selected_module") is not None:
            error_msg = "您的配置文件好像既包含智控台的配置又包含本地配置：\n"
            error_msg += "\n建议您：\n"
            error_msg += "1、将根目录的config_from_api.yaml文件复制到data下，重命名为.config.yaml\n"
            error_msg += "2、按教程配置好接口地址和密钥\n"
            raise ValueError(error_msg)
    config_file_valid = True