import os
import sys
from loguru import logger
from config.settings import load_config

def setup_logging():
    """
    从配置文件中读取日志配置，并设置日志输出格式和级别。

    该函数的主要用途是初始化日志系统，配置日志的输出格式、级别以及存储位置。
    日志可以同时输出到控制台和文件中，方便调试和问题排查。

    返回:
        logger: 配置好的日志记录器对象。
    """
    # 从配置文件中加载配置
    config = load_config()
    
    # 获取日志相关的配置项
    log_config = config["log"]
    
    # 获取日志格式配置，如果未配置则使用默认格式
    log_format = log_config.get("log_format", "<green>{time:YY-MM-DD HH:mm:ss}</green>[<light-blue>{extra[tag]}</light-blue>] - <level>{level}</level> - <light-green>{message}</light-green>")
    
    # 获取文件日志格式配置，如果未配置则使用默认格式
    log_format_simple = log_config.get("log_format_file", "{time:YYYY-MM-DD HH:mm:ss} - {name} - {level} - {extra[tag]} - {message}")
    
    # 获取日志级别配置，如果未配置则默认使用 INFO 级别
    log_level = log_config.get("log_level", "INFO")
    
    # 获取日志存储目录配置，如果未配置则默认使用 "tmp" 目录
    log_dir = log_config.get("log_dir", "tmp")
    
    # 获取日志文件名配置，如果未配置则默认使用 "server.log"
    log_file = log_config.get("log_file", "server.log")
    
    # 获取数据存储目录配置，如果未配置则默认使用 "data" 目录
    data_dir = log_config.get("data_dir", "data")

    # 创建日志目录（如果不存在）
    os.makedirs(log_dir, exist_ok=True)
    
    # 创建数据目录（如果不存在）
    os.makedirs(data_dir, exist_ok=True)

    # 移除默认的日志处理器
    logger.remove()

    # 添加控制台日志处理器
    # 使用配置的日志格式和级别，将日志输出到控制台
    logger.add(sys.stdout, format=log_format, level=log_level)

    # 添加文件日志处理器
    # 使用配置的日志格式和级别，将日志输出到指定文件
    logger.add(os.path.join(log_dir, log_file), format=log_format_simple, level=log_level)

    # 返回配置好的日志记录器对象
    return logger