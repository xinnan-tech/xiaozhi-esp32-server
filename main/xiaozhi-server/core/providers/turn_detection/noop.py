from typing import Tuple

from config.logger import setup_logging
from .base import TurnDetectionProviderBase

TAG = __name__
logger = setup_logging()


class TurnDetectionProvider(TurnDetectionProviderBase):
    """No-op Turn Detection provider (disabled mode)
    
    Always returns end_of_turn=True immediately without any network calls.
    Use this when Turn Detection is disabled.
    """
    
    def __init__(self, config: dict):
        super().__init__(config)
        logger.bind(tag=TAG).info("NoopTurnDetection initialized (Turn Detection disabled)")
    
    async def check_end_of_turn(self, text: str) -> Tuple[bool, str]:
        """Always return end_of_turn=True immediately
        
        Args:
            text: The ASR text
            
        Returns:
            Tuple of (True, text) - always signals turn finished
        """
        # No buffering needed for noop - just return the text as-is
        return True, text
