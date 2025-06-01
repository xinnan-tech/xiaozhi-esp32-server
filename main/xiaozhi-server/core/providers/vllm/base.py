from abc import ABC, abstractmethod
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


class VLLMProviderBase(ABC):
    @abstractmethod
    def response(self, question, base64_image):
        """VLLM response generator"""
        pass
