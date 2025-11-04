"""Role configuration loader factory and abstract base class.

This module provides the abstract interface for role configuration loaders
and a factory function to instantiate the appropriate loader based on
environment configuration.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from config.logger import setup_logging

from core.roles.models import RoleConfig

TAG = __name__
logger = setup_logging()


class RoleConfigLoader(ABC):
    """Abstract base class for role configuration loaders.
    
    Different storage backends (local, S3) should implement this interface.
    """
    
    @abstractmethod
    def load(self, role_id: str) -> RoleConfig:
        """Load a role configuration by its ID.
        
        Args:
            role_id: The unique identifier of the role to load.
            
        Returns:
            RoleConfig: The loaded role configuration.
            
        Raises:
            FileNotFoundError: If the role configuration is not found.
            ValueError: If the role configuration is invalid.
        """
        pass


def get_role_config_loader() -> RoleConfigLoader:
    """Factory function to get the appropriate role configuration loader.
    
    The loader type is determined by the CONFIG_STORAGE_TYPE environment variable:
    - "local" (default): Load from local filesystem
    
    Returns:
        RoleConfigLoader: An instance of the appropriate loader.
        
    Raises:
        ValueError: If an unsupported storage type is specified.
        
    Environment Variables:
        CONFIG_STORAGE_TYPE: Type of storage backend (currently only "local" is supported)
    """
    storage_type = os.getenv("CONFIG_STORAGE_TYPE", "local")
    
    logger.bind(tag=TAG).debug(f"Creating role config loader for storage type: {storage_type}")
    
    if storage_type == "local":
        from .local_loader import LocalRoleConfigLoader
        return LocalRoleConfigLoader()
    else:
        raise ValueError(
            f"Unsupported storage type: {storage_type}. "
            f"Currently only 'local' is supported"
        )

