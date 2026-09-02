import os
import sys
from loguru import logger
from config.config_loader import load_config
from config.settings import check_config_file
from datetime import datetime

SERVER_VERSION = "0.8.11"
_logger_initialized = False


def get_module_abbreviation(module_name, module_dict):
    """Get the abbreviation of the module name, return 00 if empty
    If the name contains an underscore, return the first two characters after the underscore
    """
    module_value = module_dict.get(module_name, "")
    if not module_value:
        return "00"
    if "_" in module_value:
        parts = module_value.split("_")
        return parts[-1][:2] if parts[-1] else "00"
    return module_value[:2]


def build_module_string(selected_module):
    """Build module string"""
    return (
        get_module_abbreviation("VAD", selected_module)
        + get_module_abbreviation("ASR", selected_module)
        + get_module_abbreviation("LLM", selected_module)
        + get_module_abbreviation("TTS", selected_module)
        + get_module_abbreviation("Memory", selected_module)
        + get_module_abbreviation("Intent", selected_module)
        + get_module_abbreviation("VLLM", selected_module)
    )


def formatter(record):
    """Add default value for logs without tag, and handle dynamic module string"""
    record["extra"].setdefault("tag", record["name"])
    # If selected_module is not set, use default value
    record["extra"].setdefault("selected_module", "00000000000000")
    # Extract selected_module from extra to top level to support {selected_module} format
    record["selected_module"] = record["extra"]["selected_module"]
    return record["message"]


def setup_logging():
    check_config_file()
    """Read log configuration from config file, and set log output format and level"""
    config = load_config()
    log_config = config["log"]
    global _logger_initialized

    # Configure logging on first initialization
    if not _logger_initialized:
        # Initialize with default module string
        logger.configure(
            extra={
                "selected_module": log_config.get("selected_module", "00000000000000"),
            }
        )

        log_format = log_config.get(
            "log_format",
            "<green>{time:YYMMDD HH:mm:ss}</green>[{version}_{extra[selected_module]}][<light-blue>{extra[tag]}</light-blue>]-<level>{level}</level>-<light-green>{message}</light-green>",
        )
        log_format_file = log_config.get(
            "log_format_file",
            "{time:YYYY-MM-DD HH:mm:ss} - {version}_{extra[selected_module]} - {name} - {level} - {extra[tag]} - {message}",
        )
        log_format = log_format.replace("{version}", SERVER_VERSION)
        log_format_file = log_format_file.replace("{version}", SERVER_VERSION)

        log_level = log_config.get("log_level", "INFO")
        log_dir = log_config.get("log_dir", "tmp")
        log_file = log_config.get("log_file", "server.log")
        data_dir = log_config.get("data_dir", "data")

        os.makedirs(log_dir, exist_ok=True)
        os.makedirs(data_dir, exist_ok=True)

        # Configure log output
        logger.remove()

        # Output to console
        logger.add(sys.stdout, format=log_format, level=log_level, filter=formatter, enqueue=True)

        # Output to file - unified directory, rotate by size
        # Log file full path
        log_file_path = os.path.join(log_dir, log_file)

        # Add log handler
        logger.add(
            log_file_path,
            format=log_format_file,
            level=log_level,
            filter=formatter,
            rotation="10 MB",  # Max 10MB per file
            retention="30 days",  # Keep for 30 days
            compression=None,
            encoding="utf-8",
            enqueue=True,  # Async safe
            backtrace=True,
            diagnose=True,
        )
        _logger_initialized = True  # Mark as initialized

    return logger


def create_connection_logger(selected_module_str):
    """Create independent logger for connection, bind specific module string"""
    return logger.bind(selected_module=selected_module_str)
