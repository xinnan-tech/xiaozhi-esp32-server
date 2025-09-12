from abc import ABC, abstractmethod
from typing import Optional


class VADProviderBase(ABC):

    @abstractmethod
    async def is_vad(self, conn, data) -> bool:
        """Detect voice activity in audio data"""
        pass
    
    def reset(self):
        """Reset VAD internal states. Override if needed."""
        pass
