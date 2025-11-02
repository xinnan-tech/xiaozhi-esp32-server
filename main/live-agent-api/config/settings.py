"""
Application Configuration

Centralized configuration management using Pydantic Settings.
Configuration values are loaded from environment variables.
"""

import logging
from typing import Literal
from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application Configuration
    app_env: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Application environment"
    )
    log_level: str = Field(
        default="DEBUG",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    
    # API Configuration
    api_prefix: str = Field(
        default="/api/v1",
        description="API route prefix"
    )
    
    # Database Configuration
    database_url: PostgresDsn = Field(
        ...,
        description="PostgreSQL database URL"
    )
    
    # OpenAI Configuration
    openai_api_key: str = Field(
        ...,
        description="OpenAI API key for AI features"
    )
    openai_model: str = Field(
        default="gpt-4o",
        description="OpenAI model to use for prompt generation"
    )
    
    # Snowflake ID Generator Configuration
    instance_id: int = Field(
        default=1,
        ge=0,
        le=1023,
        description="Instance ID for Snowflake ID generator (0-1023)"
    )
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    def configure_logging(self) -> None:
        """Configure application logging based on settings"""
        log_level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }
        
        level = log_level_map.get(self.log_level.upper(), logging.INFO)
        
        logging.basicConfig(
            level=level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )


# Global settings instance
settings = Settings()

