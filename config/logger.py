import os
import sys
from loguru import logger
from config.settings import load_config

def setup_logging():
    """从配置文件中读取日志配置，并设置日志输出格式和级别"""
    config = load_config()
    log_config = config["log"]
    log_format = log_config.get("log_format", "<green>{time:YY-MM-DD HH:mm:ss}</green>[<light-blue>{extra[tag]}</light-blue>] - <level>{level}</level> - <light-green>{message}</light-green>")
    log_format_simple = log_config.get("log_format_file", "{time:YYYY-MM-DD HH:mm:ss} - {name} - {level} - {extra[tag]} - {message}")
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
    logger.add(os.path.join(log_dir, log_file), format=log_format_simple, level=log_level)

    return logger
