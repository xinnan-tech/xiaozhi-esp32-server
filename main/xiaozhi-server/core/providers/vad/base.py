from abc import ABC, abstractmethod
from typing import Optional


class VADProviderBase(ABC):

    @abstractmethod
    def is_vad(self, conn, data) -> bool:
        """Detect voice activity in audio data"""
        pass
