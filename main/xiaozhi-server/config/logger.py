import os
import sys
from loguru import logger
from config.settings import load_config

SERVER_VERSION = "0.1.15"

def setup_logging():
    """从配置文件中读取日志配置，并设置日志输出格式和级别"""
    config = load_config()
    log_config = config["log"]
    log_format = log_config.get("log_format", "<green>{time:YYMMDD HH:mm:ss}</green>[{version}_{selected_module}][<light-blue>{extra[tag]}</light-blue>]-<level>{level}</level>-<light-green>{message}</light-green>")
    log_format_file = log_config.get("log_format_file", "{time:YYYY-MM-DD HH:mm:ss} - {version_{selected_module}} - {name} - {level} - {extra[tag]} - {message}")

    selected_module = config.get("selected_module")
    selected_module_str = ''.join([key[0] + value[0] for key, value in selected_module.items()])

    log_format = log_format.replace("{version}", SERVER_VERSION)
    log_format = log_format.replace("{selected_module}", selected_module_str)
    log_format_file = log_format_file.replace("{version}", SERVER_VERSION)
    log_format_file = log_format_file.replace("{selected_module}", selected_module_str)


    log_level = log_config.get("log_level", "INFO")
    log_dir = log_config.get("log_dir", "tmp")
    log_file = log_config.get("log_file", "server.log")
    data_dir = log_config.get("data_dir", "data")

    os.makedirs(log_dir, exist_ok=True)
    os.makedirs(data_dir, exist_ok=True)

    # 配置日志输出
    logger.remove()

    # 输出到控制台
    logger.add(sys.stdout, format=log_format, level=log_level)

    # 输出到文件
    logger.add(os.path.join(log_dir, log_file), format=log_format_file, level=log_level)

    return logger
