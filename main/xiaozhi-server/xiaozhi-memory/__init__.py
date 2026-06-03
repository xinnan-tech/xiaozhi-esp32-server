"""
小智记忆框架
轻量级AI记忆系统，支持多种检索模式
"""
from .core import MemoryManager, get_manager, RetrievalMode
from .memories import (
    BaseMemory, FactMemory, IntentionMemory, PreferenceMemory,
    MemoryType, MemoryStatus, IntentionStatus
)
from .llm import LLMClient, OpenAIClient

__version__ = "0.1.0"
__all__ = [
    'MemoryManager',
    'get_manager',
    'RetrievalMode',
    'BaseMemory',
    'FactMemory',
    'IntentionMemory',
    'PreferenceMemory',
    'MemoryType',
    'MemoryStatus',
    'IntentionStatus',
    'LLMClient',
    'OpenAIClient'
]
