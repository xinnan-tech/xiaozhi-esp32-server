"""
Utils package for live-agent-api

This package provides utility modules for the application,
including ID generation and response formatting.

Usage:
    from utils import id_generator
    
    # Generate ID using the global singleton instance
    new_id = id_generator.generate()
"""

from .id_generator import id_generator

__all__ = [
    "id_generator",  # Global singleton instance (recommended usage)
]
