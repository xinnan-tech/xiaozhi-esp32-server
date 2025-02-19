import os
import sys
from loguru import logger

def setup_logging(log_dir='tmp', data_dir='data'):
    """配置全局彩色日志（不同区块不同标签）"""
    os.makedirs(log_dir, exist_ok=True)
    os.makedirs(data_dir, exist_ok=True)

    # 设置日志格式，时间、日志级别、标签、消息
    log_format = (
        # "<green>{time:YYYY-MM-DD HH:mm:ss}</green>"
        "[<light-blue>{extra[tag]}</light-blue>]"
        " - <level>{level}</level> - "
        "<light-green>{message}</light-green>"
    )

    # 配置日志输出
    logger.remove()

    # 输出到控制台
    logger.add(sys.stdout, format=log_format, level="INFO")

    # 输出到文件
    logger.add(os.path.join(log_dir, "server.log"), format="{time:YYYY-MM-DD HH:mm:ss} - {name} - {level} - {extra[tag]} - {message}", level="INFO")

    return logger
