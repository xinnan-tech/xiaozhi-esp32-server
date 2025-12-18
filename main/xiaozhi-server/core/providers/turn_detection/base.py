from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
import time
import asyncio
from typing import TYPE_CHECKING

from config.logger import setup_logging

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

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
    
    Uses conn.asr_text_buffer for accumulated text (maintained by ASR).
    
    Endpoint delay mechanism:
    - When check_end_of_turn is called, first call turn detection service
    - If result is "finished", wait min_endpoint_delay
    - If result is "unfinished/waiting", wait max_endpoint_delay
    - If user continues speaking (new check_end_of_turn call), the task is cancelled
    """
    
    def __init__(self, config: dict):
        # Endpoint delay: time to wait after last speech before forcing end of turn
        # min_endpoint_delay: used when turn detection says "finished"
        # max_endpoint_delay: used when turn detection says "unfinished/waiting"
        self.min_endpoint_delay: int = config.get("min_endpoint_delay", 500)
        self.max_endpoint_delay: int = config.get("max_endpoint_delay", 2000)
        # Pending turn detection task (can be cancelled when new speech arrives)
        self._turn_detection_task: asyncio.Task = None
    
    def _cancel_pending_task(self) -> None:  # noqa: F821
        """Cancel pending turn detection task if exists"""
        if self._turn_detection_task and not self._turn_detection_task.done():
            self._turn_detection_task.cancel()
            logger.bind(tag=TAG).debug("Cancelled pending turn detection task")
            self._turn_detection_task = None
    
    def _calculate_sleep_time(self, conn: "ConnectionHandler", is_finished: bool) -> float:
        """Calculate how long to sleep based on turn detection result
        
        Args:
            conn: Connection handler containing _last_speaking_time (in ms)
            is_finished: True if turn detection says finished, False otherwise
            
        Returns:
            Sleep time in seconds (>= 0)
        """
        # Choose delay based on turn detection result
        endpoint_delay = self.min_endpoint_delay if is_finished else self.max_endpoint_delay
        
        if conn._last_speaking_time is None:
            return endpoint_delay
        
        # Convert ms to seconds for calculation
        elapsed = conn._last_speaking_time - int(time.time() * 1000)
        sleep_time = endpoint_delay - elapsed
        return sleep_time
    
    @abstractmethod
    def check_end_of_turn(self, conn: "ConnectionHandler"):
        """Check if the user has finished their turn
        
        This method manages the endpoint delay mechanism:
        1. Cancel any pending task from previous call
        2. Create a new task that:
           - Calls turn detection service with conn.asr_text_buffer
           - Wait min_endpoint_delay (if finished) or max_endpoint_delay (if unfinished)
           - If not cancelled, call conn.on_end_of_turn()
        
        Args:
            conn: Connection handler containing asr_text_buffer and _last_speaking_time
        """
        ...
    
    async def close(self) -> None:
        """Clean up resources"""
        pass
