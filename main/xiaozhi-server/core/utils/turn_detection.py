import importlib
import os
import sys
from core.providers.turn_detection.base import TurnDetectionProviderBase
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


def create_instance(class_name: str, *args, **kwargs) -> TurnDetectionProviderBase:
    """Factory method to create Turn Detection provider instance
    
    Args:
        class_name: The type name from config (e.g., "http", "noop")
        *args, **kwargs: Arguments to pass to the provider constructor
        
    Returns:
        TurnDetectionProvider instance
    """
    if os.path.exists(os.path.join("core", "providers", "turn_detection", f"{class_name}.py")):
        lib_name = f"core.providers.turn_detection.{class_name}"
        if lib_name not in sys.modules:
            sys.modules[lib_name] = importlib.import_module(lib_name)
        return sys.modules[lib_name].TurnDetectionProvider(*args, **kwargs)
    
    raise ValueError(f"Unsupported Turn Detection type: {class_name}")
