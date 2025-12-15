from typing import Tuple
import httpx

from config.logger import setup_logging
from .base import TurnDetectionProviderBase, TurnDetectionState

TAG = __name__
logger = setup_logging()


class TurnDetectionProvider(TurnDetectionProviderBase):
    """HTTP-based Turn Detection provider using httpx async client
    
    Calls an external Turn Detection service via HTTP POST.
    Gracefully degrades to end_of_turn=True on timeout or errors.
    """
    
    def __init__(self, config: dict):
        super().__init__(config)
        
        host = config.get("host", "127.0.0.1")
        port = config.get("port", 8080)
        endpoint = config.get("endpoint", "/")
        
        self.url = f"http://{host}:{port}{endpoint}"
        self.timeout = float(config.get("timeout", 0.5))
        self._client = httpx.AsyncClient(timeout=self.timeout)
        
        logger.bind(tag=TAG).info(
            f"TenTurnDetection initialized: url={self.url}, timeout={self.timeout}s"
        )
    
    async def check_end_of_turn(self, text: str) -> Tuple[bool, str]:
        """Check if the user has finished their turn via HTTP call
        
        Args:
            text: New ASR text segment
            
        Returns:
            Tuple of (end_of_turn: bool, full_text: str)
            On timeout/error, returns (True, full_text) to avoid blocking
        """
        # Append to buffer
        full_text = self._append_text(text)
        
        # Check buffer timeout
        if self._is_buffer_timeout():
            logger.bind(tag=TAG).warning(
                f"Turn buffer timeout, forcing send: '{full_text[:50]}...'"
            )
            self._clear_buffer()
            return True, full_text
        
        # Call Turn Detection service
        try:
            response = await self._client.post(
                self.url,
                json={"text": full_text}
            )
            response.raise_for_status()
            data = response.json()
            logger.bind(tag=TAG).info(f"TD raw response: {data}")
            # Parse result string
            result_str = data.get("result", "finished")
            
            if result_str == TurnDetectionState.FINISHED.value:
                logger.bind(tag=TAG).info(
                    f"Turn finished, buffering: '{full_text[:50]}'"
                )
                self._clear_buffer()
                return True, full_text
            
            # UNFINISHED or WAITING: continue buffering
            logger.bind(tag=TAG).info(
                f"Turn unfinished, buffering: '{full_text[:50]}'"
            )
            return False, full_text
            
        except httpx.TimeoutException:
            logger.bind(tag=TAG).warning(
                f"TurnDetection timeout ({self.timeout}s), defaulting to finished"
            )
            self._clear_buffer()
            return True, full_text
            
        except httpx.HTTPStatusError as e:
            logger.bind(tag=TAG).error(
                f"TurnDetection HTTP error: {e.response.status_code}, defaulting to finished"
            )
            self._clear_buffer()
            return True, full_text
            
        except Exception as e:
            logger.bind(tag=TAG).error(
                f"TurnDetection error: {e}, defaulting to finished"
            )
            self._clear_buffer()
            return True, full_text
    
    async def close(self) -> None:
        """Close the httpx client and clear buffer"""
        await super().close()
        await self._client.aclose()
        logger.bind(tag=TAG).debug("TenTurnDetection client closed")
