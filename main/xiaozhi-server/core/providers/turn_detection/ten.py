import asyncio
from typing import TYPE_CHECKING
import httpx

from config.logger import setup_logging
from .base import TurnDetectionProviderBase, TurnDetectionState

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()


class TurnDetectionProvider(TurnDetectionProviderBase):
    """HTTP-based Turn Detection provider using httpx async client
    
    Calls an external Turn Detection service via HTTP POST.
    Uses conn.asr_text_buffer for accumulated text (maintained by ASR).
    
    Implements endpoint delay mechanism:
    - First calls turn detection service to get result
    - If result is "finished", wait min_endpoint_delay
    - If result is "unfinished/waiting", wait max_endpoint_delay
    - If user continues speaking during the delay, the task is cancelled
    - After delay completes, directly calls startToChat and reports ASR
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
            f"TenTurnDetection initialized: url={self.url}, timeout={self.timeout}s, "
            f"min_endpoint_delay={self.min_endpoint_delay}ms, max_endpoint_delay={self.max_endpoint_delay}ms"
        )
    
    async def _call_turn_detection(self, full_text: str) -> bool:
        """Call Turn Detection HTTP service to get result
        
        Args:
            full_text: Accumulated text to check
            
        Returns:
            True if turn detection says finished, False otherwise
        """
        try:
            response = await self._client.post(
                self.url,
                json={"text": full_text}
            )
            response.raise_for_status()
            data = response.json()
            logger.bind(tag=TAG).info(f"TD raw response: {data}")
            
            result_str = data.get("result", "finished")
            is_finished = result_str == TurnDetectionState.FINISHED.value
            
            logger.bind(tag=TAG).info(
                f"Turn detection result: {result_str}, text: '{full_text[:50]}'"
            )
            return is_finished
            
        except httpx.TimeoutException:
            logger.bind(tag=TAG).warning(
                f"TurnDetection timeout ({self.timeout}s), defaulting to finished"
            )
            return True
            
        except httpx.HTTPStatusError as e:
            logger.bind(tag=TAG).error(
                f"TurnDetection HTTP error: {e.response.status_code}, defaulting to finished"
            )
            return True
            
        except Exception as e:
            logger.bind(tag=TAG).error(
                f"TurnDetection error: {e}, defaulting to finished"
            )
            return True

    async def _delayed_turn_detection_task(
        self,
        conn: "ConnectionHandler",
    ):
        """Task that calls turn detection, then waits for appropriate delay
        
        Flow:
        1. Call turn detection service to get result
        2. If finished: wait min_endpoint_delay
        3. If unfinished: wait max_endpoint_delay
        4. After delay completes, call startToChat and report ASR
        
        Args:
            conn: Connection handler
            
        Returns:
            True if end of turn, False if cancelled
            
        Raises:
            asyncio.CancelledError: If cancelled by new speech
        """
        full_text = conn.asr_text_buffer
        
        # Step 1: Call turn detection service
        is_finished = await self._call_turn_detection(full_text)
        
        # Step 2: Calculate sleep time based on result
        sleep_time = self._calculate_sleep_time(conn, is_finished)
        
        # Step 3: Wait for the delay
        if sleep_time > 0:
            await asyncio.sleep(sleep_time / 1000)  # Convert ms to seconds
        
        # Step 4: After delay, trigger end of turn processing
        logger.bind(tag=TAG).info("Endpoint delay completed, triggering on_end_of_turn")
        await conn.on_end_of_turn()
    
    def check_end_of_turn(self, conn: "ConnectionHandler"):
        """Check if the user has finished their turn with endpoint delay mechanism
        
        Flow:
        1. Cancel any pending task from previous call
        2. Create a new task that:
           - Calls turn detection service
           - Waits min_endpoint_delay (if finished) or max_endpoint_delay (if unfinished)
           - Calls conn.on_end_of_turn() after delay
        
        Args:
            conn: Connection handler containing asr_text_buffer and _last_speaking_time
        """
        # Step 1: Cancel pending task
        self._cancel_pending_task()
        
        logger.bind(tag=TAG).debug(
            f"check_end_of_turn called: buffer='{conn.asr_text_buffer[:50]}...'"
        )
        
        # Step 2: Create the delayed task (don't await, let it run in background)
        self._turn_detection_task = asyncio.create_task(
            self._delayed_turn_detection_task(conn)
        )
    
    async def close(self) -> None:
        """Close the httpx client"""
        await super().close()
        await self._client.aclose()
        logger.bind(tag=TAG).debug("TenTurnDetection client closed")
