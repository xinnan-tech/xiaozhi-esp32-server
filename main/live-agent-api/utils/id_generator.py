"""
ULID ID Generator

ULID (Universally Unique Lexicographically Sortable Identifier) generator.
- Zero configuration: No instance ID or epoch setup needed
- Time-sortable: IDs are naturally ordered by creation time
- URL-safe: Base32 encoded
- 128-bit: Extremely low collision probability
- Format: 26 characters (e.g., 01ARZ3NDEKTSV4RRFFQ69G5FAV)
"""
from __future__ import annotations
from typing import Optional
from ulid import ULID
import logging

logger = logging.getLogger(__name__)


class ULIDGenerator:
    """
    ULID ID Generator
    
    A singleton class for generating distributed unique IDs using ULID.
    Thread-safe and requires no configuration.
    
    Usage:
        generator = ULIDGenerator()
        id_str = generator.generate()
        id_int = generator.generate_int()
        id_uuid = generator.generate_uuid()
    """
    
    _instance: Optional['ULIDGenerator'] = None
    _initialized: bool = False
    
    def __new__(cls) -> ULIDGenerator:
        """Ensure singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """
        Initialize ULID generator
        
        Note: Due to singleton pattern, __init__ is called every time
        ULIDGenerator() is invoked, but initialization only happens once.
        """
        if not self._initialized:
            logger.info("Initializing ULID generator (singleton)")
            self.__class__._initialized = True
            logger.info("ULID generator initialized successfully")
    
    def generate(self) -> str:
        """
        Generate a unique ULID as string
        
        Returns:
            26-character ULID string (e.g., '01ARZ3NDEKTSV4RRFFQ69G5FAV')
            
        Example:
            >>> generator = ULIDGenerator()
            >>> id_str = generator.generate()
            >>> print(id_str)
            '01ARZ3NDEKTSV4RRFFQ69G5FAV'
        """
        return str(ULID())
    
    def __repr__(self) -> str:
        """String representation"""
        return f"<ULIDGenerator (singleton)>"


# Create global singleton instance
id_generator = ULIDGenerator()
