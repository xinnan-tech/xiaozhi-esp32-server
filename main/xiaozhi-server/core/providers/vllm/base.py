from abc import ABC, abstractmethod
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


class VLLMProviderBase(ABC):
    def use_multimodal_llm(self) -> bool:
        """Whether the image should be handled by the configured main LLM.

        Most visual providers answer the vision request themselves.  Providers
        that return ``True`` instead add the image to the dialogue and let the
        selected LLM complete the tool-call conversation.
        """
        return False

    @abstractmethod
    def response(self, question, base64_image):
        """VLLM response generator"""
        pass
