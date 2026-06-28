"""配置加载模块 - 从 config.yaml 读取配置，支持环境变量覆盖"""

import os
from pathlib import Path
from typing import Any

import yaml


class Settings:
    """全局配置，只读访问"""

    _instance = None
    _config: dict = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def load(cls, config_path: str | None = None) -> "Settings":
        """加载配置文件，支持环境变量覆盖"""
        instance = cls()

        # 默认配置路径
        if config_path is None:
            base_dir = Path(__file__).resolve().parent.parent.parent  # feedback-backend/
            config_path = str(base_dir / "config.yaml")

        # 读取主配置
        with open(config_path, "r", encoding="utf-8") as f:
            instance._config = yaml.safe_load(f) or {}

        # 读取自定义覆盖配置
        custom_path = Path(config_path).parent / "data" / ".config.yaml"
        if custom_path.exists():
            with open(custom_path, "r", encoding="utf-8") as f:
                custom = yaml.safe_load(f) or {}
            instance._config = _deep_merge(instance._config, custom)

        # 环境变量覆盖（FEEDBACK_ 前缀）
        instance._apply_env_overrides()

        return instance

    def _apply_env_overrides(self):
        """环境变量覆盖：FEEDBACK_DB_HOST -> database.host"""
        env_map = {
            "FEEDBACK_DB_HOST": ("database", "host"),
            "FEEDBACK_DB_PORT": ("database", "port"),
            "FEEDBACK_DB_USER": ("database", "username"),
            "FEEDBACK_DB_PASSWORD": ("database", "password"),
            "FEEDBACK_DB_NAME": ("database", "database"),
            "FEEDBACK_SERVER_HOST": ("server", "host"),
            "FEEDBACK_SERVER_PORT": ("server", "port"),
            "FEEDBACK_LLM_PROVIDER": ("llm", "provider"),
            "FEEDBACK_AUTH_SECRET": ("auth", "secret_key"),
            "FEEDBACK_ADMIN_USER": ("admin", "username"),
            "FEEDBACK_ADMIN_PASSWORD": ("admin", "password"),
            "FEEDBACK_XIAOZHI_WS_URL": ("xiaozhi", "ws_url"),
            "FEEDBACK_XIAOZHI_HTTP_URL": ("xiaozhi", "http_url"),
            "FEEDBACK_XIAOZHI_MANAGER_API_URL": ("xiaozhi", "manager_api_url"),
        }
        for env_key, path in env_map.items():
            value = os.environ.get(env_key)
            if value is not None:
                _set_nested(self._config, path, value)

        provider = self.get("llm.provider", "openai")
        llm_env_map = {
            "FEEDBACK_LLM_API_KEY": "api_key",
            "FEEDBACK_LLM_BASE_URL": "base_url",
            "FEEDBACK_LLM_MODEL": "model",
        }
        for env_key, field in llm_env_map.items():
            value = os.environ.get(env_key)
            if value is not None:
                _set_nested(self._config, ("llm", provider, field), value)

        for provider_name in ("openai", "dashscope", "deepseek"):
            prefix = f"FEEDBACK_{provider_name.upper()}"
            for suffix, field in (("API_KEY", "api_key"), ("BASE_URL", "base_url"), ("MODEL", "model")):
                value = os.environ.get(f"{prefix}_{suffix}")
                if value is not None:
                    _set_nested(self._config, ("llm", provider_name, field), value)

    # ---- 便捷属性 ----

    @property
    def server(self) -> dict:
        return self._config.get("server", {})

    @property
    def database(self) -> dict:
        return self._config.get("database", {})

    @property
    def auth(self) -> dict:
        return self._config.get("auth", {})

    @property
    def admin(self) -> dict:
        return self._config.get("admin", {})

    @property
    def llm(self) -> dict:
        return self._config.get("llm", {})

    @property
    def agent(self) -> dict:
        return self._config.get("agent", {})

    @property
    def xiaozhi(self) -> dict:
        return self._config.get("xiaozhi", {})

    @property
    def logging(self) -> dict:
        return self._config.get("logging", {})

    @property
    def database_url(self) -> str:
        """构建 SQLAlchemy 连接字符串"""
        db = self.database
        return (
            f"mysql+pymysql://{db['username']}:{db['password']}"
            f"@{db['host']}:{db['port']}/{db['database']}"
            f"?charset={db.get('charset', 'utf8mb4')}"
        )

    @property
    def database_url_async(self) -> str:
        """构建异步 SQLAlchemy 连接字符串"""
        return self.database_url.replace("mysql+pymysql", "mysql+aiomysql")

    def get(self, key_path: str, default: Any = None) -> Any:
        """点号路径访问：settings.get('server.port', 8009)"""
        keys = key_path.split(".")
        value = self._config
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return default
            if value is None:
                return default
        return value


def _deep_merge(base: dict, override: dict) -> dict:
    """递归合并字典，override 覆盖 base"""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _set_nested(config: dict, path: tuple, value: str):
    """设置嵌套字典值"""
    current = config
    for key in path[:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]
    # 类型转换：port 等数字字段
    current[path[-1]] = _auto_type(value)


def _auto_type(value: str):
    """自动类型推断"""
    if value.isdigit():
        return int(value)
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    try:
        return float(value)
    except ValueError:
        return value


# 全局单例
settings = Settings.load()
