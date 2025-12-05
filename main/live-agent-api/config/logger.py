"""Loguru logger configuration for Live Agent API"""
import os
import sys
from loguru import logger

API_VERSION = "0.1.0"
_logger_initialized = False


def setup_logging(
    log_level: str = "INFO",
    log_dir: str = "logs",
    log_file: str = "api.log",
    enable_file_logging: bool = True
):
    """
    Setup global loguru logger configuration
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory to store log files
        log_file: Log file name
        enable_file_logging: Whether to enable file logging
    
    Returns:
        Configured logger instance
    """
    global _logger_initialized
    
    if _logger_initialized:
        return logger
    
    # Console log format with colors
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    # File log format without colors
    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
        "{level: <8} | "
        "{name}:{function}:{line} | "
        "{message}"
    )
    
    # Remove default logger
    logger.remove()
    
    # Add console handler
    logger.add(
        sys.stdout,
        format=console_format,
        level=log_level,
        colorize=True,
        backtrace=True,
        diagnose=True
    )
    
    # Add file handler if enabled
    if enable_file_logging:
        os.makedirs(log_dir, exist_ok=True)
        log_file_path = os.path.join(log_dir, log_file)
        
        logger.add(
            log_file_path,
            format=file_format,
            level=log_level,
            rotation="50 MB",      # Rotate when file reaches 50MB
            retention="7 days",    # Keep logs for 7 days
            compression="zip",     # Compress rotated logs
            encoding="utf-8",
            enqueue=True,          # Async-safe
            backtrace=True,
            diagnose=True
        )
    
    _logger_initialized = True
    logger.info(f"Logger initialized - Level: {log_level}, File logging: {enable_file_logging}")
    
    return logger


def get_logger(name: str = None):
    """
    Get a logger instance with optional name binding
    
    Usage:
        from config.logger import get_logger
        
        logger = get_logger(__name__)
        logger.info("This is an info message")
    
    Args:
        name: Optional name to bind to logger (typically __name__)
    
    Returns:
        Logger instance
    """
    if not _logger_initialized:
        setup_logging()
    
    if name:
        return logger.bind(module=name)
    
    return logger

