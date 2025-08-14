import os
import sys

# Add project root directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
sys.path.insert(0, project_root)

from config.logger import setup_logging
import importlib

logger = setup_logging()

def create_instance(class_name, *args, **kwargs):
    # Create LLM instance
    if os.path.exists(os.path.join("core", "providers", "vllm", f"{class_name}.py")):
        lib_name = f"core.providers.vllm.{class_name}"
        if lib_name not in sys.modules:
            sys.modules[lib_name] = importlib.import_module(f"{lib_name}")
        return sys.modules[lib_name].VLLMProvider(*args, **kwargs)
    
    raise ValueError(f"Unsupported VLLM type: {class_name}, please check if the type configuration is correct")
