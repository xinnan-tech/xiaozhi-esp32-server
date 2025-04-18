import os
import sys
import importlib
from config.logger import setup_logging
from core.utils.util import read_config, get_project_dir

logger = setup_logging()

def create_instance(class_name, *args, **kwargs):
    if os.path.exists(os.path.join('core', 'providers', 'memory', class_name, f'{class_name}.py')):
        lib_name = f'core.providers.memory.{class_name}.{class_name}'
        if lib_name not in sys.modules:
            sys.modules[lib_name] = importlib.import_module(f'{lib_name}')
        return sys.modules[lib_name].MemoryProvider(*args, **kwargs)

    raise ValueError(f"不支持的记忆服务类型: {class_name}")

