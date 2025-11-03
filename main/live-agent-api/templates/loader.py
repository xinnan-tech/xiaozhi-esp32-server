"""
Template Loader

Utility for loading agent templates from YAML files.
"""

import yaml
import logging
from typing import Optional
from pathlib import Path
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AgentTemplate(BaseModel):
    """
    Agent template data structure
    
    Pydantic model for validating and handling agent template data.
    """
    
    wake_word: str = Field(..., description="Wake word to activate agent")
    language: str = Field(..., description="Language code (e.g., en, zh)")
    greeting: str = Field(..., description="Greeting message (maps to first_message)")
    profile: str = Field(..., description="System prompt (maps to system_prompt)")
    timezone: str = Field(default="UTC+8", description="Timezone")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "wake_word": "Hey Assistant",
                "language": "en",
                "greeting": "Hello! How can I help you?",
                "profile": "You are a helpful assistant...",
                "timezone": "UTC+8"
            }
        }
    }


class TemplateLoader:
    """
    Template loader class with static methods for loading agent templates
    
    All methods are static, no instance needed.
    """
    
    # Template directory path (relative to this file)
    TEMPLATE_DIR = Path(__file__).parent
    
    @staticmethod
    def load(template_name: str) -> Optional[AgentTemplate]:
        """
        Load agent template from YAML file
        
        Args:
            template_name: Template name (e.g., "personal_assistant", "learning_companion")
            
        Returns:
            AgentTemplate instance or None if template is "blank"
            
        Raises:
            ValueError: If template file is invalid or missing required fields
        """
        # Special case: blank template
        if template_name == "blank":
            return None
        
        # Construct template file path
        template_file = TemplateLoader.TEMPLATE_DIR / f"{template_name}.yaml"
        
        # Check if template exists
        if not template_file.exists():
            logger.error(f"Template file not found: {template_file}")
            raise ValueError(f"Template '{template_name}' does not exist")
        
        try:
            # Load YAML file
            with open(template_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            # Validate and create template using Pydantic
            template = AgentTemplate(**data)
            
            logger.info(f"Loaded template: {template_name}")
            return template
            
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML file {template_file}: {e}")
            raise ValueError(f"Template '{template_name}' has invalid YAML format: {e}")
        
        except Exception as e:
            logger.error(f"Error loading template {template_name}: {e}")
            raise
    
    @staticmethod
    def list_available() -> list[str]:
        """
        List all available template names
        
        Returns:
            List of template names (without .yaml extension)
        """
        if not TemplateLoader.TEMPLATE_DIR.exists():
            logger.warning(f"Template directory not found: {TemplateLoader.TEMPLATE_DIR}")
            return []
        
        templates = []
        for file in TemplateLoader.TEMPLATE_DIR.glob("*.yaml"):
            templates.append(file.stem)
        
        # Always include blank template
        templates.append("blank")
        
        logger.info(f"Available templates: {templates}")
        return sorted(templates)

