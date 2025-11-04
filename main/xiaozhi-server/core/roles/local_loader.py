"""Local filesystem role configuration loader implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ruamel.yaml import YAML
from config.logger import setup_logging

from core.roles.models import RoleConfig, TTSConfig
from core.roles.factory import RoleConfigLoader

TAG = __name__
logger = setup_logging()


class LocalRoleConfigLoader(RoleConfigLoader):
    """Local filesystem role configuration loader.
    
    Loads role configurations from YAML files in a local directory.
    """
    
    def __init__(self, base_path: Optional[Path] = None):
        """Initialize the local loader.
        
        Args:
            base_path: Base directory containing role YAML files.
                      Defaults to core/roles/data/ relative to this file.
        """
        if base_path is None:
            base_path = Path(__file__).resolve().parent / "data"
        
        self.base_path = Path(base_path)
        logger.bind(tag=TAG).debug(f"Initialized LocalRoleConfigLoader with base_path: {self.base_path}")
    
    def load(self, role_id: str) -> RoleConfig:
        """Load a role configuration from a local YAML file.
        
        Args:
            role_id: The unique identifier of the role (matches the YAML filename).
            
        Returns:
            RoleConfig: The loaded role configuration.
            
        Raises:
            FileNotFoundError: If the YAML file is not found.
            ValueError: If the YAML file is invalid or missing required fields.
        """
        yaml_path = self.base_path / f"{role_id}.yaml"
        
        if not yaml_path.is_file():
            raise FileNotFoundError(f"Role configuration not found: {yaml_path}")
        
        logger.bind(tag=TAG).debug(f"Loading role configuration from: {yaml_path}")
        
        try:
            yaml = YAML()
            yaml.preserve_quotes = True
            with yaml_path.open("r", encoding="utf-8") as f:
                data = yaml.load(f)
            
            if not data:
                raise ValueError(f"Empty or invalid YAML file: {yaml_path}")
            
            logger.bind(tag=TAG).debug(f"Loaded YAML data: {data}")
            
            # Parse TTS configuration (optional)
            tts_config = None
            tts_data = data.get("tts", {})
            if tts_data and isinstance(tts_data, dict):
                tts_config = TTSConfig(
                    voice_id=tts_data["voice_id"],
                    provider=tts_data["provider"]
                )
            
            # Parse language with default
            language = data.get("language", "zh")
            
            # Parse timezone with default
            timezone = data.get("timezone", "Asia/Shanghai")
            
            # Parse greeting with default
            greeting = data.get("greeting", "你好！有什么可以帮助你的吗？")
            
            # Parse wake_word with default
            wake_word = data.get("wake_word", "小智")
            
            # Create RoleConfig
            role_config = RoleConfig(
                id=data["id"],
                version=int(data["version"]),
                wake_word=wake_word,
                language=language,
                greeting=greeting,
                profile=data["profile"],
                timezone=timezone,
                tts=tts_config,
            )
            
            logger.bind(tag=TAG).info(f"Successfully loaded role configuration: {role_id}")
            return role_config
            
        except KeyError as e:
            raise ValueError(f"Missing required field in role configuration: {e}") from e
        except Exception as e:
            raise ValueError(f"Failed to parse YAML file {yaml_path}: {e}") from e

