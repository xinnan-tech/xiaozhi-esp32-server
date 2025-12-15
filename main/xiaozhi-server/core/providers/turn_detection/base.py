from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
import time
from typing import List, Optional, Tuple

from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


class TurnDetectionState(Enum):
    FINISHED = "finished"
    WAITING = "wait"
    UNFINISHED = "unfinished"


@dataclass
class TurnDetectionResult:
    """Result from Turn Detection service"""
    text: str                           # Full accumulated text
    result: TurnDetectionState          # Detection result


class TurnDetectionProviderBase(ABC):
    """Base class for Turn Detection providers
    
    Turn Detection determines whether the user has finished speaking
    and it's time for the system to respond.
    
    Manages text buffer internally - subclasses can override buffer behavior.
    """
    
    def __init__(self, config: dict):
        self._text_buffer: List[str] = []
        self._buffer_start_time: float = 0.0
        self._buffer_timeout: float = float(config.get("buffer_timeout", 10.0))
    
    def _append_text(self, text: str) -> str:
        if not self._text_buffer:
            self._buffer_start_time = time.time()
        self._text_buffer.append(text)
        return " ".join(self._text_buffer)
    
    def _clear_buffer(self) -> None:
        """Clear the text buffer"""
        self._text_buffer.clear()
        self._buffer_start_time = 0.0
    
    def _is_buffer_timeout(self) -> bool:
        """Check if buffer has timed out (to avoid infinite accumulation)"""
        if not self._text_buffer:
            return False
        return (time.time() - self._buffer_start_time) > self._buffer_timeout
    
    @abstractmethod
    async def check_end_of_turn(self, text: str) -> Tuple[bool, str]:
        """Check if the user has finished their turn
        
        Args:
            text: New ASR text segment
            
        Returns:
            Tuple of (end_of_turn: bool, full_text: str)
            - end_of_turn: True if user finished speaking, False to continue buffering
            - full_text: Accumulated text from buffer
        """
        ...
    
    async def close(self) -> None:
        """Clean up resources - clears buffer"""
        self._clear_buffer()
