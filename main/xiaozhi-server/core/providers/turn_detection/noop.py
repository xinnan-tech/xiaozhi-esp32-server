from typing import TYPE_CHECKING

from config.logger import setup_logging
from .base import TurnDetectionProviderBase

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

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
    
    def check_end_of_turn(self, conn: "ConnectionHandler"):
        """Immediately trigger end of turn (no delay)
        
        Args:
            conn: Connection handler
        """
        import asyncio
        asyncio.create_task(conn.on_end_of_turn())
