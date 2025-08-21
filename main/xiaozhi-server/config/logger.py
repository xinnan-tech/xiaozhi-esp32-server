import os
import sys
from loguru import logger
from config.config_loader import load_config
from config.settings import check_config_file
from datetime import datetime

SERVER_VERSION = "0.7.4"
_logger_initialized = False

def get_module_abbreviation(module_name, module_dict):
    """Get module name abbreviation, return 00 if empty
    
    If name contains underscore, return first two characters after underscore
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
    """Add default values for logs without tag, and handle dynamic module string"""
    record["extra"].setdefault("tag", record["name"])
    # If selected_module is not set, use default value
    record["extra"].setdefault("selected_module", "00000000000000")
    # Extract selected_module from extra to top level to support {selected_module} format
    record["selected_module"] = record["extra"]["selected_module"]

    # Filter out verbose VAD and ASR debug messages to reduce log noise
    if record["level"].name == "DEBUG":
        tag = record["extra"].get("tag", "")
        message = record["message"]

        # Filter out repetitive VAD debug messages (but keep important events)
        if "vad" in tag.lower() or "connection" in tag.lower():
            # Always keep important VAD events
            if any(phrase in message for phrase in [
                "Voice stopped after",
                "VAD states reset",
                "Cleared server speaking status"
            ]):
                # Allow these important messages to pass through
                return record["message"]
            elif any(phrase in message for phrase in [
                "VAD confidence:",
                "VAD analysis:",
                "RMS:",
                "threshold"
            ]):
                return False  # Skip repetitive messages
            # Keep VAD state changes but filter out the repetitive ones
            elif "VAD state:" in message:
                # Only show state changes, not repetitive same state logs
                if not hasattr(formatter, '_last_vad_state'):
                    formatter._last_vad_state = {}

                # Extract connection ID or use default
                connection_id = record.get("extra", {}).get("selected_module", "default")

                # Only log if state actually changed
                if connection_id not in formatter._last_vad_state or formatter._last_vad_state[connection_id] != message:
                    formatter._last_vad_state[connection_id] = message
                    # Allow this state change log to pass through
                    return record["message"]
                else:
                    return False  # Skip repeated same state

        # Filter out repetitive ASR debug messages
        if "asr" in tag.lower():
            if any(phrase in message for phrase in [
                "ASR receive_audio:",
                "have_voice=",
                "client_have_voice=",
                "audio_len=",
                "asr_buffer_len="
            ]):
                return False  # Skip this log message

        # Filter out audio packet reception messages
        if "receiveAudioHandle" in tag:
            if "Received audio packet" in message:
                return False  # Skip this log message

    return record["message"]

def update_module_string(selected_module_str):
    """Update module string"""
    logger.configure(
        extra={
            "selected_module": selected_module_str,
        }
    )

def setup_logging():
    check_config_file()
    """Read log configuration from config file and set log output format and level"""
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
            "{time:YYMMDD HH:mm:ss}[{version}_{extra[selected_module]}][{extra[tag]}]-{level}-{message}",
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
        logger.add(sys.stdout, format=log_format, level=log_level, filter=formatter)
        
        # Output to file - unified directory, rotate by size
        # Log file full path
        log_file_path = os.path.join(log_dir, log_file)
        
        # Add log handler
        logger.add(
            log_file_path,
            format=log_format_file,
            level=log_level,
            filter=formatter,
            rotation="10 MB",  # Each file maximum 10MB
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
