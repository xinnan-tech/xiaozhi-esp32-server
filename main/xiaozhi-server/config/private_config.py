import os
import time
import yaml
from config.logger import setup_logging
from typing import Dict, Any, Optional
from copy import deepcopy
from core.utils.util import get_project_dir
from core.utils import llm, tts
from core.utils.lock_manager import FileLockManager

# 定义当前模块的标签，用于日志记录
TAG = __name__

class PrivateConfig:
    """
    设备私有配置管理类。

    该类用于管理设备的私有配置，包括加载、更新、删除配置，以及创建私有模块实例。
    配置存储在 YAML 文件中，支持多设备配置管理。
    """

    def __init__(self, device_id: str, default_config: Dict[str, Any], auth_code_gen=None):
        """
        初始化私有配置管理类。

        Args:
            device_id (str): 设备唯一标识。
            default_config (Dict[str, Any]): 默认配置字典。
            auth_code_gen: 认证码生成器（可选）。
        """
        self.device_id = device_id  # 设备唯一标识
        self.default_config = default_config  # 默认配置
        self.config_path = get_project_dir() + 'data/.private_config.yaml'  # 配置文件路径
        self.logger = setup_logging()  # 日志记录器
        self.private_config = {}  # 当前设备的私有配置
        self.auth_code_gen = auth_code_gen  # 认证码生成器
        self.lock_manager = FileLockManager()  # 文件锁管理器，用于并发控制

    async def load_or_create(self):
        """
        加载或创建设备的私有配置。

        如果配置文件不存在或设备配置不存在，则根据默认配置创建新的设备配置。
        """
        try:
            # 获取文件锁，确保并发安全
            await self.lock_manager.acquire_lock(self.config_path)
            try:
                # 检查配置文件是否存在
                if os.path.exists(self.config_path):
                    # 读取配置文件
                    with open(self.config_path, 'r', encoding='utf-8') as f:
                        all_configs = yaml.safe_load(f) or {}
                else:
                    # 如果文件不存在，初始化空配置
                    all_configs = {}

                # 检查当前设备的配置是否存在
                if self.device_id not in all_configs:
                    # 获取默认配置中的模块选择
                    selected_modules = self.default_config['selected_module']
                    selected_tts = selected_modules['TTS']
                    selected_llm = selected_modules['LLM']
                    selected_asr = selected_modules['ASR']
                    selected_vad = selected_modules['VAD']

                    # 生成认证码（如果提供了认证码生成器）
                    auth_code = None
                    if self.auth_code_gen:
                        auth_code = self.auth_code_gen.generate_code()

                    # 初始化设备配置
                    device_config = {
                        'selected_module': deepcopy(selected_modules),  # 选择的模块
                        'prompt': self.default_config['prompt'],  # 提示词配置
                        'LLM': {
                            selected_llm: deepcopy(self.default_config['LLM'][selected_llm])
                        },
                        'TTS': {
                            selected_tts: deepcopy(self.default_config['TTS'][selected_tts])
                        },
                        'ASR': {
                            selected_asr: deepcopy(self.default_config['ASR'][selected_asr])
                        },
                        'VAD': {
                            selected_vad: deepcopy(self.default_config['VAD'][selected_vad])
                        },
                        'auth_code': auth_code  # 认证码
                    }
                    
                    # 将新配置添加到所有配置中
                    all_configs[self.device_id] = device_config
                    
                    # 保存更新后的配置到文件
                    with open(self.config_path, 'w', encoding='utf-8') as f:
                        yaml.dump(all_configs, f, allow_unicode=True)

                # 设置当前设备的私有配置
                self.private_config = all_configs[self.device_id]

            finally:
                # 释放文件锁
                self.lock_manager.release_lock(self.config_path)

        except Exception as e:
            # 记录错误日志
            self.logger.bind(tag=TAG).error(f"Error handling private config: {e}")
            self.private_config = {}

    async def update_config(self, selected_modules: Dict[str, str], prompt: str, nickname: str) -> bool:
        """
        更新设备配置。

        Args:
            selected_modules (Dict[str, str]): 选择的模块配置，格式如 {'LLM': 'AliLLM', 'TTS': 'EdgeTTS',...}
            prompt (str): 提示词配置
            nickname (str): 设备昵称

        Returns:
            bool: 更新是否成功
        """
        try:
            # 获取文件锁，确保并发安全
            await self.lock_manager.acquire_lock(self.config_path)
            try:
                # 读取默认配置
                main_config = self.default_config

                # 创建新的设备配置
                device_config = {
                    'selected_module': selected_modules,
                    'prompt': prompt,
                    'nickname': nickname,
                }
                # 保留上次聊天时间（如果存在）
                if self.private_config.get('last_chat_time'):
                    device_config['last_chat_time'] = self.private_config['last_chat_time']
                # 保留所有者信息（如果存在）
                if self.private_config.get('owner'):
                    device_config['owner'] = self.private_config['owner']

                # 从默认配置中复制完整的模块配置
                for module_type, selected_name in selected_modules.items():
                    if selected_name and selected_name in main_config.get(module_type, {}):
                        device_config[module_type] = {
                            selected_name: main_config[module_type][selected_name]
                        }

                # 读取所有配置
                if os.path.exists(self.config_path):
                    with open(self.config_path, 'r', encoding='utf-8') as f:
                        all_configs = yaml.safe_load(f) or {}
                else:
                    all_configs = {}

                # 更新当前设备的配置
                all_configs[self.device_id] = device_config
                self.private_config = device_config

                # 保存更新后的配置到文件
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    yaml.dump(all_configs, f, allow_unicode=True)

                return True
            finally:
                # 释放文件锁
                self.lock_manager.release_lock(self.config_path)

        except Exception as e:
            # 记录错误日志
            self.logger.bind(tag=TAG).error(f"Error updating config: {e}")
            return False

    async def delete_config(self) -> bool:
        """
        删除设备配置。

        Returns:
            bool: 删除是否成功
        """
        try:
            # 获取文件锁，确保并发安全
            await self.lock_manager.acquire_lock(self.config_path)
            try:
                # 读取所有配置
                if os.path.exists(self.config_path):
                    with open(self.config_path, 'r', encoding='utf-8') as f:
                        all_configs = yaml.safe_load(f) or {}
                else:
                    return False

                # 删除当前设备的配置
                if self.device_id in all_configs:
                    del all_configs[self.device_id]
                    
                    # 保存更新后的配置到文件
                    with open(self.config_path, 'w', encoding='utf-8') as f:
                        yaml.dump(all_configs, f, allow_unicode=True)
                    
                    # 清空当前设备的私有配置
                    self.private_config = {}
                    return True
                
                return False
            finally:
                # 释放文件锁
                self.lock_manager.release_lock(self.config_path)

        except Exception as e:
            # 记录错误日志
            self.logger.bind(tag=TAG).error(f"Error deleting config: {e}")
            return False

    def create_private_instances(self):
        """
        创建私有模块实例。

        根据私有配置创建 LLM 和 TTS 模块的实例。

        Returns:
            Tuple: 返回 LLM 和 TTS 模块的实例，如果配置不存在则返回 (None, None)。
        """
        # 检查私有配置是否存在
        if not self.private_config:
            self.logger.bind(tag=TAG).error("Private config not found for device_id: {}", self.device_id)
            return None, None
        
        # 获取配置中的模块选择
        config = self.private_config
        selected_modules = config['selected_module']
        return (
            llm.create_instance(
                selected_modules["LLM"]
                if not 'type' in config["LLM"][selected_modules["LLM"]]
                else
                config["LLM"][selected_modules["LLM"]]['type'],
                config["LLM"][selected_modules["LLM"]],
            ),
            tts.create_instance(
                selected_modules["TTS"]
                if not 'type' in config["TTS"][selected_modules["TTS"]]
                else
                config["TTS"][selected_modules["TTS"]]["type"],
                config["TTS"][selected_modules["TTS"]],
                self.default_config.get("delete_audio", True)  # 使用默认配置中的全局设置
            )
        )

    async def update_last_chat_time(self, timestamp=None):
        """
        更新设备最近一次的聊天时间。

        Args:
            timestamp: 指定的时间戳，如果不传则使用当前时间。

        Returns:
            bool: 更新是否成功
        """
        if not self.private_config:
            self.logger.bind(tag=TAG).error("Private config not found")
            return False
            
        try:
            # 获取文件锁，确保并发安全
            await self.lock_manager.acquire_lock(self.config_path)
            try:
                # 如果未提供时间戳，则使用当前时间
                if timestamp is None:
                    timestamp = int(time.time())
                    
                # 更新最近聊天时间
                self.private_config['last_chat_time'] = timestamp
                
                # 读取所有配置
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    all_configs = yaml.safe_load(f) or {}
                    
                # 更新当前设备的配置
                all_configs[self.device_id] = self.private_config
                
                # 保存更新后的配置到文件
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    yaml.dump(all_configs, f, allow_unicode=True)
                    
                return True
            finally:
                # 释放文件锁
                self.lock_manager.release_lock(self.config_path)
                
        except Exception as e:
            # 记录错误日志
            self.logger.bind(tag=TAG).error(f"Error updating last chat time: {e}")
            return False

    def get_auth_code(self) -> str:
        """
        获取设备的认证码。

        Returns:
            str: 认证码，如果没有则返回空字符串。
        """
        return self.private_config.get('auth_code', '')

    def get_owner(self) -> Optional[str]:
        """
        获取设备当前所有者。

        Returns:
            Optional[str]: 所有者信息，如果没有则返回 None。
        """
        return self.private_config.get('owner')