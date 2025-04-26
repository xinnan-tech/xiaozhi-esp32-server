import os
import sys
from loguru import logger
from config.config_loader import load_config

SERVER_VERSION = "0.3.12"


def get_module_abbreviation(module_name, module_dict):
    """获取模块名称的缩写，如果为空则返回00"""
    return (
        module_dict.get(module_name, "")[:2] if module_dict.get(module_name) else "00"
    )


def build_module_string(selected_module):
    """构建模块字符串"""
    return (
        get_module_abbreviation("VAD", selected_module)
        + get_module_abbreviation("ASR", selected_module)
        + get_module_abbreviation("LLM", selected_module)
        + get_module_abbreviation("TTS", selected_module)
        + get_module_abbreviation("Memory", selected_module)
        + get_module_abbreviation("Intent", selected_module)
    )


def formatter(record):
    """为没有 tag 的日志添加默认值"""
    record["extra"].setdefault("tag", record["name"])
    return record["message"]


def setup_logging():
    """从配置文件中读取日志配置，并设置日志输出格式和级别"""
    config = load_config()
    log_config = config["log"]
    log_format = log_config.get(
        "log_format",
        "<green>{time:YYMMDD HH:mm:ss}</green>[{version}_{selected_module}][<light-blue>{extra[tag]}</light-blue>]-<level>{level}</level>-<light-green>{message}</light-green>",
    )
    log_format_file = log_config.get(
        "log_format_file",
        "{time:YYYY-MM-DD HH:mm:ss} - {version_{selected_module}} - {name} - {level} - {extra[tag]} - {message}",
    )
    selected_module_str = build_module_string(config.get("selected_module", {}))

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
    logger.add(sys.stdout, format=log_format, level=log_level, filter=formatter)

    # 输出到文件
    logger.add(
        os.path.join(log_dir, log_file),
        format=log_format_file,
        level=log_level,
        filter=formatter,
    )

    return logger
