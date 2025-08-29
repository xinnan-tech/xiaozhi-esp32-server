import importlib
from config.logger import setup_logging
import os
import sys
# Add project root directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
sys.path.insert(0, project_root)


logger = setup_logging()


def create_instance(class_name, *args, **kwargs):
    # Create LLM instance
    
    # Try relative path first (original behavior)
    provider_path = os.path.join('core', 'providers', 'llm', class_name, f'{class_name}.py')
    
    # If relative path doesn't work, try absolute path from project root
    if not os.path.exists(provider_path):
        provider_path = os.path.join(project_root, 'core', 'providers', 'llm', class_name, f'{class_name}.py')
    
    # Debug logging
    logger.bind(tag=__name__).info(f"Looking for LLM provider: {class_name}")
    logger.bind(tag=__name__).info(f"Current working directory: {os.getcwd()}")
    logger.bind(tag=__name__).info(f"Project root: {project_root}")
    logger.bind(tag=__name__).info(f"Provider path: {provider_path}")
    logger.bind(tag=__name__).info(f"Provider exists: {os.path.exists(provider_path)}")
    
    if os.path.exists(provider_path):
        lib_name = f'core.providers.llm.{class_name}.{class_name}'
        logger.bind(tag=__name__).info(f"Loading module: {lib_name}")
        
        if lib_name not in sys.modules:
            try:
                sys.modules[lib_name] = importlib.import_module(f'{lib_name}')
                logger.bind(tag=__name__).info(f"Successfully imported: {lib_name}")
            except ImportError as e:
                logger.bind(tag=__name__).error(f"Failed to import {lib_name}: {e}")
                raise ValueError(f"Failed to import LLM provider {class_name}: {e}")
        
        return sys.modules[lib_name].LLMProvider(*args, **kwargs)
    
    # Enhanced error message with debugging info
    cwd = os.getcwd()
    available_providers = []
    llm_dir = os.path.join(project_root, 'core', 'providers', 'llm')
    if os.path.exists(llm_dir):
        available_providers = [d for d in os.listdir(llm_dir) 
                             if os.path.isdir(os.path.join(llm_dir, d)) and d != '__pycache__']
    
    error_msg = (f"Unsupported LLM type: {class_name}\n"
                f"Current working directory: {cwd}\n"
                f"Project root: {project_root}\n"
                f"Searched path: {provider_path}\n"
                f"Available providers: {available_providers}")
    
    logger.bind(tag=__name__).error(error_msg)
    raise ValueError(error_msg)
