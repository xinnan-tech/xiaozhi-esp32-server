import os
import yaml
from collections.abc import Mapping
from typing import Any, Dict, Optional, Type, TypeVar, Union, get_type_hints, get_origin, get_args
from dataclasses import dataclass, field, fields, MISSING
import inspect
from config.manage_api_client import init_service, get_server_config, get_agent_models

T = TypeVar('T')


class ConfigDict(dict):
    """增强的配置字典，支持点号访问和嵌套获取"""
    
    def __init__(self, data: Dict[str, Any] = None):
        super().__init__()
        if data:
            for key, value in data.items():
                if isinstance(value, dict):
                    self[key] = ConfigDict(value)
                else:
                    self[key] = value
    
    def __getattr__(self, key: str) -> Any:
        """支持点号访问"""
        try:
            return self[key]
        except KeyError:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{key}'")
    
    def __setattr__(self, key: str, value: Any) -> None:
        """支持点号设置"""
        self[key] = value
    
    def __getitem__(self, key: str) -> Any:
        """重写[]访问，支持嵌套路径，找不到抛出KeyError"""
        if '.' in key:
            keys = key.split('.')
            current = self
            for k in keys:
                if not isinstance(current, (dict, ConfigDict)):
                    raise KeyError(f"Cannot access '{k}' on non-dict object")
                current = super(ConfigDict, current).__getitem__(k)
            return current
        return super().__getitem__(key)
    
    def get(self, key: str, default: Any = None) -> Any:
        """重写get方法，支持嵌套路径"""
        try:
            return self[key]
        except KeyError:
            return default
    
    def __setitem__(self, key: str, value: Any) -> None:
        """重写[]设置，支持嵌套路径"""
        if '.' in key:
            keys = key.split('.')
            current = self
            for k in keys[:-1]:
                if k not in current:
                    current[k] = ConfigDict()
                elif not isinstance(current[k], (dict, ConfigDict)):
                    current[k] = ConfigDict()
                current = current[k]
            
            if isinstance(value, dict) and not isinstance(value, ConfigDict):
                value = ConfigDict(value)
            super(ConfigDict, current).__setitem__(keys[-1], value)
        else:
            if isinstance(value, dict) and not isinstance(value, ConfigDict):
                value = ConfigDict(value)
            super().__setitem__(key, value)


class ConfigField:
    """配置字段，模仿dataclass的field功能"""
    
    def __init__(self, default=MISSING, default_factory=MISSING, prefix: str = None):
        self.default = default
        self.default_factory = default_factory
        self.prefix = prefix
        
        if default is not MISSING and default_factory is not MISSING:
            raise ValueError("Cannot specify both default and default_factory")


def config_field(default=MISSING, default_factory=MISSING, prefix: str = None):
    """创建配置字段"""
    return ConfigField(default, default_factory, prefix)


def _is_config_class(cls: Type) -> bool:
    """检查类是否是ConfigurationProperties装饰的配置类"""
    return hasattr(cls, '_config_prefix') and hasattr(cls, '_inject_config')


def _create_nested_config_instance(config_class: Type, config: ConfigDict, config_path: str):
    """创建嵌套配置类实例"""
    try:
        # 获取嵌套配置数据 - 直接传递整个config，让嵌套类自己处理前缀
        # 因为嵌套类有自己的prefix，它会从config中正确提取数据
        return config_class(config)
    except Exception as e:
        # 如果创建失败，返回None或抛出更详细的错误
        raise ValueError(f"Failed to create nested config instance for {config_class.__name__} at path '{config_path}': {e}")


def ConfigurationProperties(prefix: str = "", auto_inject: bool = True):
    """
    配置属性装饰器，模仿Spring Boot的@ConfigurationProperties
    
    Args:
        prefix: 配置前缀，如 'server.database'
        auto_inject: 是否自动注入配置
    """
    def decorator(cls: Type[T]) -> Type[T]:
        if not inspect.isclass(cls):
            raise TypeError("ConfigurationProperties can only be applied to classes")
        
        # 保存原始的__init__方法
        original_init = cls.__init__ if hasattr(cls, '__init__') else None
        
        # 获取类的类型注解
        type_hints = get_type_hints(cls)
        
        def new_init(self, config: ConfigDict = None, **kwargs):
            # 如果有原始的__init__，先调用它
            if original_init and original_init is not object.__init__:
                try:
                    original_init(self)
                except TypeError:
                    # 如果原始__init__不接受参数，忽略
                    pass
            
            if config is None:
                # 如果没有传入config，尝试从全局获取
                config = getattr(self.__class__, '_global_config', None)
                if config is None:
                    return
            
            # 注入配置
            self._inject_config(config, prefix, **kwargs)
        
        def _inject_config(self, config: ConfigDict, config_prefix: str = "", **overrides):
            """注入配置到实例属性"""
            # 处理类属性
            for attr_name in dir(self.__class__):
                if attr_name.startswith('_'):
                    continue
                    
                attr_value = getattr(self.__class__, attr_name)
                if isinstance(attr_value, ConfigField):
                    # 确定配置路径
                    field_prefix = attr_value.prefix or config_prefix
                    config_path = f"{field_prefix}.{attr_name}" if field_prefix else attr_name
                    
                    # 从overrides或config获取值
                    if attr_name in overrides:
                        value = overrides[attr_name]
                    else:
                        # 检查是否有类型注解，如果是嵌套配置类则特殊处理
                        attr_type = type_hints.get(attr_name)
                        if attr_type and inspect.isclass(attr_type) and _is_config_class(attr_type):
                            # 嵌套配置类，创建实例
                            try:
                                value = _create_nested_config_instance(attr_type, config, config_path)
                            except ValueError as e:
                                # 如果创建失败，使用默认值
                                print(f"Warning: {e}")
                                if attr_value.default_factory is not MISSING:
                                    value = attr_value.default_factory()
                                else:
                                    value = attr_value.default
                        else:
                            # 普通类型，使用默认值逻辑
                            if attr_value.default_factory is not MISSING:
                                default_val = attr_value.default_factory()
                            else:
                                default_val = attr_value.default
                            
                            value = config.get(config_path, default_val)
                    
                    setattr(self, attr_name, value)
            
            # 处理类型注解的属性
            for attr_name, attr_type in type_hints.items():
                if hasattr(self, attr_name):
                    continue  # 已经通过ConfigField处理过了
                
                config_path = f"{config_prefix}.{attr_name}" if config_prefix else attr_name
                
                if attr_name in overrides:
                    value = overrides[attr_name]
                else:
                    # 检查是否是嵌套的ConfigurationProperties类
                    if inspect.isclass(attr_type) and _is_config_class(attr_type):
                        # 创建嵌套配置类实例
                        try:
                            value = _create_nested_config_instance(attr_type, config, config_path)
                        except ValueError as e:
                            # 如果创建失败，使用None或默认值
                            print(f"Warning: {e}")
                            value = None
                    else:
                        # 普通类型，直接从配置获取
                        value = config.get(config_path)
                
                if value is not None:
                    setattr(self, attr_name, value)
        
        # 添加方法到类
        cls.__init__ = new_init
        cls._inject_config = _inject_config
        cls._config_prefix = prefix
        
        # 添加类方法用于设置全局配置
        @classmethod
        def set_global_config(cls, config: ConfigDict):
            cls._global_config = config
        
        cls.set_global_config = set_global_config
        
        return cls
    
    return decorator


def get_project_dir():
    """获取项目根目录"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/"


def read_config(config_path):
    with open(config_path, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
    return config


def load_config():
    """加载配置文件"""
    from core.utils.cache.manager import cache_manager, CacheType

    # 检查缓存
    cached_config = cache_manager.get(CacheType.CONFIG, "main_config")
    if cached_config is not None:
        # 确保返回的是ConfigDict类型
        if not isinstance(cached_config, ConfigDict):
            cached_config = ConfigDict(cached_config)
        return cached_config

    default_config_path = get_project_dir() + "config.yaml"
    custom_config_path = get_project_dir() + "data/.config.yaml"

    # 加载默认配置
    default_config = read_config(default_config_path)
    custom_config = read_config(custom_config_path)

    if custom_config.get("manager-api", {}).get("url"):
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            # 如果已经在事件循环中，使用异步版本
            config = asyncio.run_coroutine_threadsafe(
                get_config_from_api_async(custom_config), loop
            ).result()
        except RuntimeError:
            # 如果不在事件循环中（启动时），创建新的事件循环
            config = asyncio.run(get_config_from_api_async(custom_config))
    else:
        # 合并配置
        config = merge_configs(default_config, custom_config)
    
    # 转换为ConfigDict
    config = ConfigDict(config)
    
    # 初始化目录
    ensure_directories(config)

    # 缓存配置
    cache_manager.set(CacheType.CONFIG, "main_config", config)
    return config


async def get_config_from_api_async(config):
    """从Java API获取配置（异步版本）"""
    # 初始化API客户端
    init_service(config)

    # 获取服务器配置
    config_data = await get_server_config()
    if config_data is None:
        raise Exception("Failed to fetch server config from API")

    config_data["read_config_from_api"] = True
    config_data["manager-api"] = {
        "url": config["manager-api"].get("url", ""),
        "secret": config["manager-api"].get("secret", ""),
    }
    auth_enabled = config_data.get("server", {}).get("auth", {}).get("enabled", False)
    # server的配置以本地为准
    if config.get("server"):
        config_data["server"] = {
            "ip": config["server"].get("ip", ""),
            "port": config["server"].get("port", ""),
            "http_port": config["server"].get("http_port", ""),
            "vision_explain": config["server"].get("vision_explain", ""),
            "auth_key": config["server"].get("auth_key", ""),
        }
    config_data["server"]["auth"] = {"enabled": auth_enabled}
    # 如果服务器没有prompt_template，则从本地配置读取
    if not config_data.get("prompt_template"):
        config_data["prompt_template"] = config.get("prompt_template")
    return ConfigDict(config_data)


async def get_private_config_from_api(config, device_id, client_id):
    """从Java API获取私有配置"""
    return await get_agent_models(device_id, client_id, config["selected_module"])


def ensure_directories(config):
    """确保所有配置路径存在"""
    dirs_to_create = set()
    project_dir = get_project_dir()  # 获取项目根目录
    # 日志文件目录
    log_dir = config.get("log", {}).get("log_dir", "tmp")
    dirs_to_create.add(os.path.join(project_dir, log_dir))

    # ASR/TTS模块输出目录
    for module in ["ASR", "TTS"]:
        if config.get(module) is None:
            continue
        for provider in config.get(module, {}).values():
            output_dir = provider.get("output_dir", "")
            if output_dir:
                dirs_to_create.add(output_dir)

    # 根据selected_module创建模型目录
    selected_modules = config.get("selected_module", {})
    for module_type in ["ASR", "LLM", "TTS"]:
        selected_provider = selected_modules.get(module_type)
        if not selected_provider:
            continue
        if config.get(module) is None:
            continue
        if config.get(selected_provider) is None:
            continue
        provider_config = config.get(module_type, {}).get(selected_provider, {})
        output_dir = provider_config.get("output_dir")
        if output_dir:
            full_model_dir = os.path.join(project_dir, output_dir)
            dirs_to_create.add(full_model_dir)

    # 统一创建目录（保留原data目录创建）
    for dir_path in dirs_to_create:
        try:
            os.makedirs(dir_path, exist_ok=True)
        except PermissionError:
            print(f"警告：无法创建目录 {dir_path}，请检查写入权限")


def merge_configs(default_config, custom_config):
    """
    递归合并配置，custom_config优先级更高

    Args:
        default_config: 默认配置
        custom_config: 用户自定义配置

    Returns:
        合并后的配置
    """
    if not isinstance(default_config, Mapping) or not isinstance(
        custom_config, Mapping
    ):
        return custom_config

    merged = dict(default_config)

    for key, value in custom_config.items():
        if (
            key in merged
            and isinstance(merged[key], Mapping)
            and isinstance(value, Mapping)
        ):
            merged[key] = merge_configs(merged[key], value)
        else:
            merged[key] = value

    return merged


# 导出主要的类和函数
__all__ = [
    'ConfigDict', 
    'ConfigField', 
    'config_field', 
    'ConfigurationProperties',
    'load_config',
    'get_project_dir',
    'merge_configs'
]


# 配置类定义

@ConfigurationProperties(prefix="server.database")
class DatabaseConfig:
    """数据库配置类"""
    host: str = config_field(default="localhost")
    port: int = config_field(default=3306)
    username: str = config_field(default="root")
    password: str = config_field(default="")
    database: str = config_field(default="xiaozhi")


@ConfigurationProperties(prefix="server.redis")
class RedisConfig:
    """Redis配置类"""
    host: str = config_field(default="localhost")
    port: int = config_field(default=6379)
    password: str = config_field(default="")
    db: int = config_field(default=0)


@ConfigurationProperties(prefix="mqtt_server")
class MQTTServerConfig:
    """MQTT服务器配置类"""
    enabled: bool = config_field(default=False)
    host: str = config_field(default="0.0.0.0")
    port: int = config_field(default=1883)
    udp_port: int = config_field(default=1883)
    public_ip: str = config_field(default="localhost")
    max_connections: int = config_field(default=1000)
    heartbeat_interval: int = config_field(default=30)
    max_payload_size: int = config_field(default=8192)


@ConfigurationProperties(prefix="server")
class ServerConfig:
    """服务器配置类"""
    ip: str = config_field(default="0.0.0.0")
    port: int = config_field(default=8080)
    http_port: int = config_field(default=8081)
    auth_key: str = config_field(default="")
    vision_explain: str = config_field(default="")
    
    # 嵌套配置类
    database: DatabaseConfig = config_field(default_factory=lambda: DatabaseConfig())
    redis: RedisConfig = config_field(default_factory=lambda: RedisConfig())
    mqtt_server: MQTTServerConfig = config_field(default_factory=lambda: MQTTServerConfig())


@ConfigurationProperties(prefix="asr.whisper")
class WhisperConfig:
    """Whisper ASR配置类"""
    model: str = config_field(default="base")
    language: str = config_field(default="zh")
    device: str = config_field(default="cpu")


@ConfigurationProperties(prefix="asr")
class ASRConfig:
    """ASR配置类"""
    provider: str = config_field(default="whisper")
    # 嵌套配置
    whisper: WhisperConfig = config_field(default_factory=lambda: WhisperConfig())


@ConfigurationProperties(prefix="selected_module")
class SelectedModuleConfig:
    """选中模块配置类"""
    ASR: str = config_field(default="")
    TTS: str = config_field(default="")
    LLM: str = config_field(default="")
    VLLM: str = config_field(default="")
    VAD: str = config_field(default="")
    Memory: str = config_field(default="")
    Intent: str = config_field(default="")


@ConfigurationProperties(prefix="log")
class LogConfig:
    """日志配置类"""
    log_dir: str = config_field(default="tmp")
    level: str = config_field(default="INFO")


@ConfigurationProperties(prefix="protocols")
class ProtocolConfig:
    """协议配置类"""
    enabled_protocols: list = config_field(default_factory=lambda: ["websocket"])
    websocket_enabled: bool = config_field(default=True)
    mqtt_enabled: bool = config_field(default=False)


@ConfigurationProperties(prefix="")
class MainConfig:
    """主配置类，包含常用的顶级配置"""
    read_config_from_api: bool = config_field(default=False)
    exit_commands: list = config_field(default_factory=list)
    close_connection_no_voice_time: int = config_field(default=120)
    xiaozhi: str = config_field(default="")
    prompt: str = config_field(default="")
    delete_audio: bool = config_field(default=True)
    
    # 协议配置
    protocols: ProtocolConfig = config_field(default_factory=lambda: ProtocolConfig())


@ConfigurationProperties(prefix="voiceprint")
class VoiceprintConfig:
    """声纹配置类"""
    enabled: bool = config_field(default=False)
    model_path: str = config_field(default="")
    threshold: float = config_field(default=0.5)


# 全局配置实例
_global_config_dict: ConfigDict = None
_server_config: ServerConfig = None
_selected_module_config: SelectedModuleConfig = None
_log_config: LogConfig = None
_main_config: MainConfig = None
_voiceprint_config: VoiceprintConfig = None
_mqtt_server_config: MQTTServerConfig = None
_protocol_config: ProtocolConfig = None


def get_config_instance(config_class: Type[T]) -> T:
    """获取配置类实例的工厂方法"""
    global _global_config_dict
    if _global_config_dict is None:
        _global_config_dict = load_config()
    
    return config_class(_global_config_dict)


def get_server_config() -> ServerConfig:
    """获取服务器配置实例"""
    global _server_config
    if _server_config is None:
        _server_config = get_config_instance(ServerConfig)
    return _server_config


def get_selected_module_config() -> SelectedModuleConfig:
    """获取选中模块配置实例"""
    global _selected_module_config
    if _selected_module_config is None:
        _selected_module_config = get_config_instance(SelectedModuleConfig)
    return _selected_module_config


def get_log_config() -> LogConfig:
    """获取日志配置实例"""
    global _log_config
    if _log_config is None:
        _log_config = get_config_instance(LogConfig)
    return _log_config


def get_main_config() -> MainConfig:
    """获取主配置实例"""
    global _main_config
    if _main_config is None:
        _main_config = get_config_instance(MainConfig)
    return _main_config


def get_voiceprint_config() -> VoiceprintConfig:
    """获取声纹配置实例"""
    global _voiceprint_config
    if _voiceprint_config is None:
        _voiceprint_config = get_config_instance(VoiceprintConfig)
    return _voiceprint_config


def get_mqtt_server_config() -> MQTTServerConfig:
    """获取MQTT服务器配置实例"""
    global _mqtt_server_config
    if _mqtt_server_config is None:
        _mqtt_server_config = get_config_instance(MQTTServerConfig)
    return _mqtt_server_config


def get_protocol_config() -> ProtocolConfig:
    """获取协议配置实例"""
    global _protocol_config
    if _protocol_config is None:
        _protocol_config = get_config_instance(ProtocolConfig)
    return _protocol_config


def refresh_config():
    """刷新所有配置实例"""
    global _global_config_dict, _server_config, _selected_module_config, _log_config, _main_config, _voiceprint_config, _mqtt_server_config, _protocol_config
    _global_config_dict = None
    _server_config = None
    _selected_module_config = None
    _log_config = None
    _main_config = None
    _voiceprint_config = None
    _mqtt_server_config = None
    _protocol_config = None
