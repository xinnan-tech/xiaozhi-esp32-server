import os
import sys

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
sys.path.insert(0, project_root)

from config.logger import setup_logging
import importlib
import re

logger = setup_logging()


_VALID_CLASS_NAME = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


def _build_llm_module_map():
    module_map = {}
    base_dir = os.path.join(project_root, 'core', 'providers', 'llm')
    if not os.path.isdir(base_dir):
        return module_map

    for name in os.listdir(base_dir):
        if not _VALID_CLASS_NAME.fullmatch(name):
            continue
        provider_file = os.path.join(base_dir, name, f'{name}.py')
        if os.path.isfile(provider_file):
            module_map[name] = f'core.providers.llm.{name}.{name}'

    return module_map


LLM_MODULE_MAP = _build_llm_module_map()


def create_instance(class_name, *args, **kwargs):
    # 创建LLM实例
    if not isinstance(class_name, str) or not _VALID_CLASS_NAME.fullmatch(class_name):
        raise ValueError(f"不支持的LLM类型: {class_name}，请检查该配置的type是否设置正确")

    lib_name = LLM_MODULE_MAP.get(class_name)
    if lib_name:
        if lib_name not in sys.modules:
            sys.modules[lib_name] = importlib.import_module(lib_name)
        return sys.modules[lib_name].LLMProvider(*args, **kwargs)

    raise ValueError(f"不支持的LLM类型: {class_name}，请检查该配置的type是否设置正确")
