"""Role configuration system for AI agents."""

from .models import RoleConfig, TTSConfig
from .factory import RoleConfigLoader, get_role_config_loader
from .local_loader import LocalRoleConfigLoader

__all__ = [
    "RoleConfig",
    "TTSConfig",
    "RoleConfigLoader",
    "LocalRoleConfigLoader",
    "get_role_config_loader",
]

